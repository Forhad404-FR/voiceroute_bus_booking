"""Read-only catalogue queries: districts, routes, schedules and seat maps.
All reports/filters run inside MySQL via parameterised SQL (SQLAlchemy text())."""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.timeutil import now_bd_naive
from app.services.district_parser import parse_route_text, resolve
from app.services.seats import SEATS_PER_ROW, build_layout
from app.services.serializers import row_to_dict, rows_to_dicts

HUBS = ("Dhaka", "Chattogram")

SCHEDULE_SELECT = """
SELECT s.id, s.departure_date, s.departure_time, s.arrival_time, s.fare,
       s.total_seats, s.available_seats, s.status,
       b.bus_name, b.bus_type, o.operator_name,
       r.id AS route_id, r.distance_km, r.estimated_duration_minutes AS duration_minutes,
       sd.district_name AS origin, dd.district_name AS destination,
       ss.station_name AS origin_station, ds.station_name AS destination_station
  FROM schedules s
  JOIN buses b                ON b.id = s.bus_id
  JOIN transport_operators o  ON o.id = b.operator_id
  JOIN routes r               ON r.id = s.route_id
  JOIN stations ss            ON ss.id = r.source_station_id
  JOIN districts sd           ON sd.id = ss.district_id
  JOIN stations ds            ON ds.id = r.destination_station_id
  JOIN districts dd           ON dd.id = ds.district_id
"""


def decorate_schedule(d: dict) -> dict:
    """Add presentation fields derived from already-fetched columns."""
    d["bus_type_label"] = "AC" if d.get("bus_type") == "AC" else "Non-AC"
    d["is_sample_data"] = True
    try:
        h, m = (int(x) for x in str(d["departure_time"]).split(":")[:2])
        d["arrival_day_offset"] = (h * 60 + m + int(d.get("duration_minutes") or 0)) // 1440
    except (ValueError, KeyError):
        d["arrival_day_offset"] = 0
    return d


# ---------------------------------------------------------------- districts
def list_districts(conn: Connection) -> list[dict]:
    rows = conn.execute(text("SELECT id, district_name AS name, slug FROM districts ORDER BY id")).mappings().all()
    return rows_to_dicts(rows)


def search_districts(conn: Connection, q: str, exclude: str | None = None) -> list[dict]:
    districts = list_districts(conn)
    names = [d["name"] for d in districts]
    matched = set(resolve(q, names).candidates) if q.strip() else set(names)
    if exclude:
        ex = resolve(exclude, names).exact
        if ex:
            matched.discard(ex)
    return [d for d in districts if d["name"] in matched]


def canonical_district(conn: Connection, name: str | None) -> str | None:
    if not name or not name.strip():
        return None
    names = [d["name"] for d in list_districts(conn)]
    return resolve(name, names).exact


def parse_route(conn: Connection, q: str) -> dict:
    names = [d["name"] for d in list_districts(conn)]
    p = parse_route_text(q, names)
    return {
        "understood": p.understood,
        "origin": p.origin,
        "destination": p.destination,
        "origin_text": p.origin_text,
        "destination_text": p.destination_text,
        "origin_candidates": p.origin_candidates,
        "destination_candidates": p.destination_candidates,
    }


# ---------------------------------------------------------------- routes
_ROUTE_EXISTS = """
SELECT r.id, r.distance_km, r.estimated_duration_minutes AS duration_minutes
  FROM routes r
  JOIN stations ss  ON ss.id = r.source_station_id
  JOIN districts sd ON sd.id = ss.district_id
  JOIN stations ds  ON ds.id = r.destination_station_id
  JOIN districts dd ON dd.id = ds.district_id
 WHERE sd.district_name = :o AND dd.district_name = :d
"""


def find_routes(conn: Connection, origin: str, destination: str) -> list[dict]:
    return rows_to_dicts(conn.execute(text(_ROUTE_EXISTS), {"o": origin, "d": destination}).mappings().all())


def connecting_hubs(conn: Connection, origin: str, destination: str) -> list[dict]:
    """Hubs that have a direct route on BOTH legs (origin->hub and hub->destination)."""
    hubs = []
    for hub in HUBS:
        if hub in (origin, destination):
            continue
        leg1 = find_routes(conn, origin, hub)
        leg2 = find_routes(conn, hub, destination)
        if leg1 and leg2:
            hubs.append({"hub": hub, "leg1": f"{origin} to {hub}", "leg2": f"{hub} to {destination}"})
    return hubs


def route_search(conn: Connection, origin: str, destination: str) -> dict:
    routes = find_routes(conn, origin, destination)
    if routes:
        return {"direct": True, "origin": origin, "destination": destination, "routes": routes,
                "message": f"Direct buses run from {origin} to {destination}.", "hubs": []}
    return {
        "direct": False, "origin": origin, "destination": destination, "routes": [],
        "message": f"No direct bus available from {origin} to {destination}.",
        "hubs": connecting_hubs(conn, origin, destination),
    }


def popular_routes(conn: Connection, limit: int = 8) -> list[dict]:
    sql = """
    SELECT sd.district_name AS origin, dd.district_name AS destination,
           r.distance_km, COUNT(DISTINCT bk.id) AS bookings,
           (SELECT MIN(s2.fare) FROM schedules s2 WHERE s2.route_id = r.id AND s2.status = 'ACTIVE') AS from_fare
      FROM routes r
      JOIN stations ss  ON ss.id = r.source_station_id
      JOIN districts sd ON sd.id = ss.district_id
      JOIN stations ds  ON ds.id = r.destination_station_id
      JOIN districts dd ON dd.id = ds.district_id
      LEFT JOIN schedules s  ON s.route_id = r.id
      LEFT JOIN bookings bk  ON bk.schedule_id = s.id AND bk.booking_status IN ('CONFIRMED','COMPLETED')
     WHERE sd.district_name IN ('Dhaka', 'Chattogram')
     GROUP BY r.id, sd.district_name, dd.district_name, r.distance_km
     ORDER BY bookings DESC,
              (dd.district_name IN ('Chattogram','Dhaka','Sylhet','Cox''s Bazar','Rajshahi','Khulna')) DESC,
              r.distance_km DESC, r.id
     LIMIT :lim
    """
    return rows_to_dicts(conn.execute(text(sql), {"lim": limit}).mappings().all())


# ---------------------------------------------------------------- schedules
def search_schedules(conn: Connection, origin: str, destination: str, travel_date: date,
                     sort: str = "departure", bus_type: str | None = None,
                     only_available: bool = False) -> list[dict]:
    clauses = [
        "sd.district_name = :o", "dd.district_name = :d", "s.departure_date = :dt",
        "s.status = 'ACTIVE'", "b.is_active = 1",
        "TIMESTAMP(s.departure_date, s.departure_time) > :now",
    ]
    params: dict = {"o": origin, "d": destination, "dt": travel_date, "now": now_bd_naive()}
    if bus_type in ("AC", "NON_AC"):
        clauses.append("b.bus_type = :bt")
        params["bt"] = bus_type
    if only_available:
        clauses.append("s.available_seats > 0")
    order = "s.fare ASC, s.departure_time ASC" if sort == "price" else "s.departure_time ASC, s.fare ASC"
    sql = SCHEDULE_SELECT + " WHERE " + " AND ".join(clauses) + " ORDER BY " + order
    return [decorate_schedule(row_to_dict(r)) for r in conn.execute(text(sql), params).mappings().all()]


def get_schedule(conn: Connection, schedule_id: int) -> dict | None:
    row = conn.execute(text(SCHEDULE_SELECT + " WHERE s.id = :id"), {"id": schedule_id}).mappings().first()
    return decorate_schedule(row_to_dict(row)) if row else None


def seat_map(conn: Connection, schedule_id: int) -> dict | None:
    sched = get_schedule(conn, schedule_id)
    if not sched:
        return None
    booked = {
        r[0] for r in conn.execute(
            text("SELECT seat_number FROM booking_seats WHERE schedule_id = :id AND seat_status = 'BOOKED'"),
            {"id": schedule_id},
        ).all()
    }
    return {
        "schedule": sched,
        "seats_per_row": SEATS_PER_ROW,
        "aisle_after_col": 2,
        "seats": build_layout(int(sched["total_seats"]), booked),
        "booked_count": len(booked),
    }
