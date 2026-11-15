"""Integration tests against a REAL MySQL 8 database (API + triggers + transactions + concurrency).

Run (use a dedicated EMPTY test database, never production):
    export TEST_DATABASE_URL='mysql+pymysql://user:pass@host:3306/voiceroute_test'
    pip install -r backend/requirements-dev.txt
    pytest tests -v
Skipped automatically when TEST_DATABASE_URL is not set.
"""
import os
import threading
from datetime import timedelta

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")

if os.getenv("TEST_DATABASE_URL"):
    from fastapi.testclient import TestClient
    from sqlalchemy import text

    from app.core.security import hash_password
    from app.database.init_db import init_database
    from app.database.session import get_engine
    from app.main import app
    from app.services import bookings as svc


@pytest.fixture(scope="session")
def engine():
    eng = get_engine()
    init_database(eng, log=lambda *_: None)
    init_database(eng, log=lambda *_: None)  # second run proves initialisation is repeatable
    with eng.begin() as c:
        phones = "('01700000001','01700000002','01700000003','01700000009')"   # leftovers from earlier runs
        c.execute(text(f"DELETE FROM bookings WHERE user_id IN (SELECT id FROM users WHERE phone_number IN {phones})"))
        c.execute(text(f"DELETE FROM users WHERE phone_number IN {phones}"))
        c.execute(text("INSERT INTO users (full_name, phone_number, password_hash, role) VALUES "
                       "('Test Admin','01700000009',:h,'ADMIN')"), {"h": hash_password("AdminPass123")})
    return eng


@pytest.fixture()
def client(engine):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def _login(client, phone, pw):
    r = client.post("/api/auth/login", json={"phone_number": phone, "password": pw})
    assert r.status_code == 200, r.text
    client.headers["X-CSRF-Token"] = client.cookies.get("vr_csrf")
    return r


def _register(client, name, phone, pw="Passw0rd123"):
    r = client.post("/api/auth/register", json={"full_name": name, "phone_number": phone, "password": pw, "confirm_password": pw})
    client.headers["X-CSRF-Token"] = client.cookies.get("vr_csrf", "")
    return r


@pytest.fixture()
def user_id(engine):
    with engine.begin() as c:
        c.execute(text("INSERT IGNORE INTO users (full_name, phone_number, password_hash) VALUES ('DB Tester','01700000003',:h)"),
                  {"h": hash_password("Passw0rd123")})
        return c.execute(text("SELECT id FROM users WHERE phone_number='01700000003'")).scalar()


def _fresh_schedule(engine, seats=8, status="ACTIVE"):
    """A brand-new future schedule so each test starts from a known seat count."""
    with engine.begin() as c:
        bus = c.execute(text("SELECT id FROM buses ORDER BY id LIMIT 1")).scalar()
        route = c.execute(text("SELECT id FROM routes ORDER BY id LIMIT 1")).scalar()
        n = c.execute(text("SELECT COUNT(*) FROM schedules")).scalar()
        d = c.execute(text("SELECT DATE_ADD(UTC_DATE(), INTERVAL 60 DAY)")).scalar() + timedelta(days=0)
        res = c.execute(text("INSERT INTO schedules (bus_id, route_id, departure_date, departure_time, arrival_time, fare, total_seats, available_seats, status) "
                             "VALUES (:b,:r,:d,SEC_TO_TIME(:t),'23:00',500.00,:s,:s,:st)"),
                        {"b": bus, "r": route, "d": d, "t": 3600 + (n % 80000), "s": seats, "st": status})
        return res.lastrowid


def _avail(engine, sid):
    with engine.connect() as c:
        return c.execute(text("SELECT available_seats FROM schedules WHERE id=:i"), {"i": sid}).scalar()


# ------------------------------------------------------------------ API: auth & catalogue
def test_health_and_districts(client):
    assert client.get("/api/health").json()["status"] == "ok"
    d = client.get("/api/districts").json()["districts"]
    assert len(d) == 30


def test_autocomplete_api(client):
    names = [x["name"] for x in client.get("/api/districts/search", params={"q": "C"}).json()["districts"]]
    assert names == ["Chattogram", "Cumilla", "Cox's Bazar", "Chandpur"]
    names = [x["name"] for x in client.get("/api/districts/search", params={"q": "C", "exclude": "Chattogram"}).json()["districts"]]
    assert "Chattogram" not in names


def test_register_login_duplicate_and_hashing(client, engine):
    assert _register(client, "Reg User", "01700000001").status_code == 201
    assert _register(client, "Reg User", "01700000001").status_code == 409
    with engine.connect() as c:
        h = c.execute(text("SELECT password_hash FROM users WHERE phone_number='01700000001'")).scalar()
    assert h.startswith("$2") and "Passw0rd123" not in h
    assert client.post("/api/auth/login", json={"phone_number": "01700000001", "password": "wrong-pass1"}).status_code == 401
    _login(client, "01700000001", "Passw0rd123")
    assert client.get("/api/auth/me").json()["user"]["phone_number"] == "01700000001"


def test_route_and_schedule_search(client):
    from app.core.timeutil import today_bd
    d = (today_bd() + timedelta(days=1)).isoformat()
    r = client.get("/api/schedules/search", params={"origin": "Dhaka", "destination": "Chittagong", "date": d}).json()
    assert r["direct"] and r["destination"] == "Chattogram" and len(r["schedules"]) >= 1
    assert all(s["origin"] == "Dhaka" and s["destination"] == "Chattogram" for s in r["schedules"])
    n = client.get("/api/schedules/search", params={"origin": "Sylhet", "destination": "Khulna", "date": d}).json()
    assert n["direct"] is False and n["schedules"] == [] and {h["hub"] for h in n["hubs"]} == {"Dhaka", "Chattogram"}


def test_two_hub_route_counts(engine):
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM routes")).scalar() == 114   # 29*4 - 2 duplicates
        assert c.execute(text("SELECT COUNT(*) FROM (SELECT source_station_id, destination_station_id FROM routes GROUP BY 1,2 HAVING COUNT(*)>1) x")).scalar() == 0
        assert c.execute(text("SELECT COUNT(*) FROM schedules s LEFT JOIN buses b ON b.id=s.bus_id LEFT JOIN routes r ON r.id=s.route_id WHERE b.id IS NULL OR r.id IS NULL")).scalar() == 0
        assert c.execute(text("SELECT MIN(cnt) FROM (SELECT route_id, COUNT(*) cnt FROM schedules GROUP BY route_id, departure_date) x")).scalar() >= 2


# ------------------------------------------------------------------ API: booking flow
def test_booking_cancel_flow_and_ownership(client, engine):
    sid = _fresh_schedule(engine, seats=10)
    assert client.post("/api/bookings", json={"schedule_id": sid, "seat_numbers": [1]}).status_code == 401  # unauthenticated
    _register(client, "Owner", "01700000002")
    r = client.post("/api/bookings", json={"schedule_id": sid, "seat_numbers": [1, 2], "total_fare": 1})  # price field ignored
    assert r.status_code == 201, r.text
    b = r.json()["booking"]
    assert float(b["total_fare"]) == 1000.0 and b["seat_numbers"] == [1, 2] and _avail(engine, sid) == 8
    assert client.post("/api/bookings", json={"schedule_id": sid, "seat_numbers": [2]}).status_code == 409
    assert client.post("/api/bookings", json={"schedule_id": sid, "seat_numbers": [99]}).status_code == 422
    assert [x["id"] for x in client.get("/api/bookings/my").json()["bookings"]] == [b["id"]]

    other = TestClient(app, base_url="http://testserver")           # a different user cannot see/cancel it
    _register(other, "Intruder", "01700000003")
    assert other.get(f"/api/bookings/{b['id']}").status_code == 404
    assert other.post(f"/api/bookings/{b['id']}/cancel").status_code == 404
    assert other.get("/api/bookings/my").json()["bookings"] == []

    assert client.post(f"/api/bookings/{b['id']}/cancel").status_code == 200
    assert _avail(engine, sid) == 10
    assert client.post(f"/api/bookings/{b['id']}/cancel").status_code == 409   # no double cancel / double restore
    assert _avail(engine, sid) == 10
    assert client.post("/api/bookings", json={"schedule_id": sid, "seat_numbers": [1, 2]}).status_code == 201  # seats reusable
    with engine.connect() as c:
        acts = [r[0] for r in c.execute(text("SELECT action FROM audit_logs WHERE booking_id=:i ORDER BY id"), {"i": b["id"]})]
    assert acts == ["BOOKING_CREATED", "BOOKING_CANCELLED"]


def test_booking_references_unique(client, engine):
    sid = _fresh_schedule(engine, seats=12)
    _register(client, "Ref User", "01700000002")
    refs = {client.post("/api/bookings", json={"schedule_id": sid, "seat_numbers": [i]}).json()["booking"]["booking_reference"] for i in range(1, 6)}
    assert len(refs) == 5


def test_admin_authorisation(client):
    _register(client, "Normal", "01700000002")
    for path in ["/api/admin/dashboard", "/api/admin/users", "/api/admin/buses", "/api/admin/audit-logs"]:
        assert client.get(path).status_code == 403
    admin = TestClient(app, base_url="http://testserver")
    _login(admin, "01700000009", "AdminPass123")
    dash = admin.get("/api/admin/dashboard")
    assert dash.status_code == 200 and dash.json()["totals"]["total_routes"] == 114
    for path in ["/api/admin/bookings", "/api/admin/users", "/api/admin/buses", "/api/admin/schedules", "/api/admin/audit-logs", "/api/admin/low-seat-alerts"]:
        assert admin.get(path).status_code == 200
    assert TestClient(app).get("/api/admin/dashboard").status_code == 401


def test_admin_bus_crud(engine):
    admin = TestClient(app, base_url="http://testserver")
    _login(admin, "01700000009", "AdminPass123")
    op = admin.get("/api/admin/operators").json()["operators"][0]["id"]
    body = {"operator_id": op, "bus_name": "Test Bus", "bus_type": "AC", "registration_number": "TEST-0001", "total_seats": 20, "is_active": True}
    with engine.begin() as c:
        c.execute(text("DELETE FROM buses WHERE registration_number='TEST-0001'"))
    r = admin.post("/api/admin/buses", json=body); assert r.status_code == 201
    bid = r.json()["id"]
    assert admin.post("/api/admin/buses", json=body).status_code == 409
    assert admin.put(f"/api/admin/buses/{bid}", json={**body, "bus_name": "Renamed"}).status_code == 200
    assert admin.delete(f"/api/admin/buses/{bid}").status_code == 200


# ------------------------------------------------------------------ DB: triggers / transactions / concurrency
def test_triggers_exist(engine):
    with engine.connect() as c:
        names = {r[0] for r in c.execute(text("SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = DATABASE()"))}
    assert {"trg_bookings_after_insert", "trg_bookings_after_update", "trg_schedules_after_update"} <= names


def test_foreign_keys_enforced(engine):
    with pytest.raises(Exception), engine.begin() as c:
        c.execute(text("INSERT INTO bookings (booking_reference,user_id,schedule_id,seat_count,total_fare) VALUES ('VR-FKTEST0001',99999999,99999999,1,1)"))


def test_low_seat_alert_lifecycle(engine, user_id):
    sid = _fresh_schedule(engine, seats=8)                       # threshold = 5
    b1 = svc.create_booking(engine, user_id, sid, [1, 2])        # 6 left -> no alert
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM low_seat_alerts WHERE schedule_id=:s"), {"s": sid}).scalar() == 0
    b2 = svc.create_booking(engine, user_id, sid, [3])           # 5 left -> alert opens
    svc.create_booking(engine, user_id, sid, [4])                # 4 left -> same alert refreshed, not duplicated
    with engine.connect() as c:
        rows = c.execute(text("SELECT available_seats, resolved_at FROM low_seat_alerts WHERE schedule_id=:s"), {"s": sid}).all()
    assert len(rows) == 1 and rows[0][0] == 4 and rows[0][1] is None
    svc.cancel_booking(engine, b1["id"], user_id)                # 6 left -> recovers, alert resolved
    with engine.connect() as c:
        assert c.execute(text("SELECT resolved_at IS NOT NULL FROM low_seat_alerts WHERE schedule_id=:s"), {"s": sid}).scalar() == 1


def test_trigger_blocks_second_cancel_and_non_confirmed_restore(engine, user_id):
    sid = _fresh_schedule(engine, seats=8)
    b = svc.create_booking(engine, user_id, sid, [1])
    svc.cancel_booking(engine, b["id"], user_id)
    assert _avail(engine, sid) == 8
    with pytest.raises(Exception), engine.begin() as c:           # status is final at DB level
        c.execute(text("UPDATE bookings SET booking_status='CANCELLED' WHERE id=:i"), {"i": b["id"]})
    with pytest.raises(Exception), engine.begin() as c:
        c.execute(text("UPDATE bookings SET booking_status='CONFIRMED' WHERE id=:i"), {"i": b["id"]})
    assert _avail(engine, sid) == 8
    with engine.begin() as c:                                      # unchanged status -> nothing restored
        b2 = svc.create_booking(engine, user_id, sid, [2])
        c.execute(text("UPDATE bookings SET cancelled_at=NULL WHERE id=:i"), {"i": b2["id"]})
    assert _avail(engine, sid) == 7


def test_rollback_preserves_seat_counts(engine, user_id):
    sid = _fresh_schedule(engine, seats=8)
    with pytest.raises(RuntimeError):
        with engine.begin() as c:
            c.execute(text("INSERT INTO bookings (booking_reference,user_id,schedule_id,seat_count,total_fare) VALUES ('VR-ROLLBACK01',:u,:s,2,1000)"), {"u": user_id, "s": sid})
            assert c.execute(text("SELECT available_seats FROM schedules WHERE id=:s"), {"s": sid}).scalar() == 6
            raise RuntimeError("boom")
    assert _avail(engine, sid) == 8
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM bookings WHERE booking_reference='VR-ROLLBACK01'")).scalar() == 0


def test_database_blocks_double_booked_seat_even_without_app_checks(engine, user_id):
    sid = _fresh_schedule(engine, seats=8)
    b1 = svc.create_booking(engine, user_id, sid, [1])
    with pytest.raises(Exception), engine.begin() as c:
        c.execute(text("INSERT INTO bookings (booking_reference,user_id,schedule_id,seat_count,total_fare) VALUES ('VR-RAWDUP0001',:u,:s,1,500)"), {"u": user_id, "s": sid})
        bid = c.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        c.execute(text("INSERT INTO booking_seats (booking_id,schedule_id,seat_number) VALUES (:b,:s,1)"), {"b": bid, "s": sid})
    assert _avail(engine, sid) == 7 and b1["seat_numbers"] == [1]


def test_concurrent_booking_of_last_seat(engine, user_id):
    sid = _fresh_schedule(engine, seats=8)
    for i in range(1, 8):
        svc.create_booking(engine, user_id, sid, [i])            # leave exactly one seat (#8)
    assert _avail(engine, sid) == 1
    results, barrier = [], threading.Barrier(6)

    def attempt():
        barrier.wait()
        try:
            svc.create_booking(engine, user_id, sid, [8]); results.append("ok")
        except svc.BookingError as e:
            results.append(e.status_code)

    threads = [threading.Thread(target=attempt) for _ in range(6)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert results.count("ok") == 1 and results.count(409) == 5
    assert _avail(engine, sid) == 0
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM booking_seats WHERE schedule_id=:s AND seat_number=8 AND seat_status='BOOKED'"), {"s": sid}).scalar() == 1


def test_sql_analytics_valid(engine):
    from app.services import admin as a
    with engine.connect() as c:
        d = a.dashboard(c)
        assert d["totals"]["total_routes"] == 114 and d["totals"]["total_districts"] == 30
        assert isinstance(a.list_audit_logs(c), list) and isinstance(a.list_low_seat_alerts(c), list)
