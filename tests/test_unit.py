"""Pure-logic unit tests (no database needed)."""
import re
from pathlib import Path

import pytest

from app.core.config import ConfigError, build_engine_config
from app.core.security import (create_access_token, decode_access_token, new_booking_reference,
                               normalize_phone, validate_password_strength)
from app.database.sqlsplit import split_sql
from app.services.district_parser import parse_route_text, resolve
from app.services.seats import build_layout, seat_label, validate_seat_selection

DB_DIR = Path(__file__).resolve().parents[1] / "database"
SEED = (DB_DIR / "seed.sql").read_text()
DISTRICTS = [d.replace("''", "'") for d in re.findall(r"\('([^']+(?:''[^']*)?)','[a-z\-]+'\)", SEED.split("-- 2.")[0])]


def test_exactly_30_districts_in_seed():
    assert len(DISTRICTS) == 30 and len(set(DISTRICTS)) == 30
    assert DISTRICTS[0] == "Dhaka" and DISTRICTS[-1] == "Tangail" and "Cox's Bazar" in DISTRICTS


@pytest.mark.parametrize("q,expected", [
    ("Dha", ["Dhaka"]), ("F", ["Feni"]),
    ("C", ["Chattogram", "Cumilla", "Cox's Bazar", "Chandpur"]),
    ("S", ["Sylhet", "Sunamganj", "Sirajganj", "Satkhira"]),
    ("chit", ["Chattogram"]), ("barisal", ["Barishal"]), ("jessore", ["Jashore"]), ("comilla", ["Cumilla"]),
])
def test_autocomplete_matching(q, expected):
    assert resolve(q, DISTRICTS).candidates == expected


def test_no_match_returns_empty():
    assert resolve("Zzz", DISTRICTS).candidates == []


@pytest.mark.parametrize("text,o,d", [
    ("Dhaka to Chittagong", "Dhaka", "Chattogram"),
    ("I want to go from Dhaka to Sylhet.", "Dhaka", "Sylhet"),
    ("Find buses from Dhaka to Cumilla", "Dhaka", "Cumilla"),
    ("Show me buses to Cox's Bazar", None, "Cox's Bazar"),
    ("Sylhet to Dhaka", "Sylhet", "Dhaka"),
    ("from barisal to jessore", "Barishal", "Jashore"),
    ("dhaka to dhaka", "Dhaka", None),
])
def test_route_parser(text, o, d):
    p = parse_route_text(text, DISTRICTS)
    assert (p.origin, p.destination) == (o, d)


def test_route_parser_partial_destination():
    p = parse_route_text("Dhaka to C", DISTRICTS)
    assert p.origin == "Dhaka" and p.destination is None
    assert p.destination_candidates == ["Chattogram", "Cumilla", "Cox's Bazar", "Chandpur"]


def test_route_parser_gibberish_not_understood():
    assert parse_route_text("blah blah", DISTRICTS).understood is False


def test_seat_validation():
    assert validate_seat_selection([1, 2], 40) is None
    assert validate_seat_selection([], 40)
    assert validate_seat_selection([1, 1], 40)
    assert validate_seat_selection([0], 40) and validate_seat_selection([41], 40)
    assert validate_seat_selection(list(range(1, 8)), 40)  # more than 6


def test_seat_layout():
    layout = build_layout(8, {2})
    assert [s["label"] for s in layout][:5] == ["A1", "A2", "A3", "A4", "B1"]
    assert layout[1]["status"] == "BOOKED" and layout[0]["status"] == "AVAILABLE"
    assert seat_label(1) == "A1"


def test_password_rules_and_phone():
    assert validate_password_strength("short1")
    assert validate_password_strength("onlyletters")
    assert validate_password_strength("Passw0rdOK") is None
    assert normalize_phone("+880 1712-345678") == "01712345678"
    with pytest.raises(ValueError):
        normalize_phone("12345")


def test_booking_references_unique_and_unpredictable():
    refs = {new_booking_reference() for _ in range(2000)}
    assert len(refs) == 2000 and all(re.fullmatch(r"VR-[A-Z2-9]{10}", r) for r in refs)


def test_jwt_roundtrip_and_tamper():
    import jwt
    t = create_access_token(7, "s" * 40, 5)
    assert decode_access_token(t, "s" * 40)["sub"] == "7"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(t, "x" * 40)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(t + "a", "s" * 40)


def test_database_url_translation():
    url, args = build_engine_config("mysql://u:p@host:3306/db?ssl-mode=REQUIRED")
    assert url.startswith("mysql+pymysql://") and "ssl" not in url and "charset=utf8mb4" in url and "ssl" in args
    with pytest.raises(ConfigError):
        build_engine_config("sqlite:///x.db")
    with pytest.raises(ConfigError):
        build_engine_config("postgresql://u:p@h/db")


def test_missing_env_gives_clear_error(monkeypatch):
    from app.core import config
    config.get_settings.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: None, raising=False)
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        config.get_settings()
    config.get_settings.cache_clear()


def test_sql_splitter_keeps_trigger_bodies_whole():
    stmts = split_sql((DB_DIR / "triggers.sql").read_text())
    creates = [s for s in stmts if s.startswith("CREATE TRIGGER")]
    assert len(creates) == 6 and all(s.rstrip().endswith("END") for s in creates)
    assert split_sql("SELECT 'a;b'; SELECT 2;") == ["SELECT 'a;b'", "SELECT 2"]


def test_sql_files_static_contract():
    schema = (DB_DIR / "schema.sql").read_text()
    trig = (DB_DIR / "triggers.sql").read_text()
    for t in ["users", "districts", "stations", "transport_operators", "buses", "routes", "schedules",
              "bookings", "booking_seats", "audit_logs", "low_seat_alerts"]:
        assert f"CREATE TABLE IF NOT EXISTS {t} " in schema
    assert schema.count("ENGINE=InnoDB") == schema.count("CREATE TABLE")
    assert "uq_schedule_active_seat" in schema and "DECIMAL(10,2)" in schema
    assert "AFTER INSERT ON bookings" in trig and "AFTER UPDATE ON bookings" in trig
    assert "OLD.booking_status = 'CONFIRMED' AND NEW.booking_status = 'CANCELLED'" in trig
    demo = (DB_DIR / "demo_queries.sql").read_text()
    for kw in ["GROUP BY", "HAVING", "LEFT JOIN", "INNER", "FOR UPDATE", "SUM(", "COUNT(", "ROLLBACK", "NOT EXISTS", "IN ("]:
        assert kw in demo or kw == "INNER"
