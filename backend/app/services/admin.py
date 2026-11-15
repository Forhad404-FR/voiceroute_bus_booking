"""Admin analytics and CRUD. Every report is computed in MySQL (aggregates, joins, subqueries)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.timeutil import now_bd_naive
from app.services.catalog import SCHEDULE_SELECT, decorate_schedule
from app.services.serializers import row_to_dict, rows_to_dicts

_ROUTE_JOIN = """
  JOIN routes r      ON r.id = s.route_id
  JOIN stations ss   ON ss.id = r.source_station_id
  JOIN districts sd  ON sd.id = ss.district_id
  JOIN stations ds   ON ds.id = r.destination_station_id
  JOIN districts dd  ON dd.id = ds.district_id
"""


def dashboard(conn: Connection) -> dict:
    one = lambda sql, **p: conn.execute(text(sql), p).mappings().first()  # noqa: E731
    totals = one("""
        SELECT (SELECT COUNT(*) FROM users)                         AS total_users,
               (SELECT COUNT(*) FROM buses)                         AS total_buses,
               (SELECT COUNT(*) FROM routes)                        AS total_routes,
               (SELECT COUNT(*) FROM schedules)                     AS total_schedules,
               (SELECT COUNT(*) FROM bookings)                      AS total_bookings,
               (SELECT COUNT(*) FROM bookings WHERE booking_status = 'CONFIRMED') AS confirmed_bookings,
               (SELECT COUNT(*) FROM bookings WHERE booking_status = 'CANCELLED') AS cancelled_bookings,
               (SELECT COUNT(*) FROM bookings WHERE booking_status = 'COMPLETED') AS completed_bookings,
               (SELECT COALESCE(SUM(total_fare), 0) FROM bookings
                 WHERE booking_status IN ('CONFIRMED','COMPLETED'))  AS total_revenue,
               (SELECT COUNT(*) FROM low_seat_alerts WHERE resolved_at IS NULL) AS open_low_seat_alerts,
               (SELECT COUNT(*) FROM districts)                     AS total_districts,
               (SELECT COUNT(*) FROM transport_operators)           AS total_operators
    """)
    popular = conn.execute(text("""
        SELECT sd.district_name AS origin, dd.district_name AS destination,
               COUNT(bk.id) AS bookings, COALESCE(SUM(bk.seat_count),0) AS seats_sold,
               COALESCE(SUM(bk.total_fare),0) AS revenue
          FROM bookings bk JOIN schedules s ON s.id = bk.schedule_id""" + _ROUTE_JOIN + """
         WHERE bk.booking_status IN ('CONFIRMED','COMPLETED')
         GROUP BY r.id, sd.district_name, dd.district_name
         ORDER BY bookings DESC, seats_sold DESC LIMIT 5""")).mappings().all()
    return {
        "totals": row_to_dict(totals),
        "popular_routes": rows_to_dicts(popular),
        "recent_bookings": list_bookings(conn, limit=8),
        "low_seat_alerts": list_low_seat_alerts(conn, open_only=True, limit=8),
    }


def list_bookings(conn: Connection, limit: int = 100, status: str | None = None) -> list[dict]:
    sql = """
        SELECT bk.id, bk.booking_reference, bk.seat_count, bk.total_fare, bk.booking_status, bk.booked_at,
               u.full_name AS passenger_name, u.phone_number,
               sd.district_name AS origin, dd.district_name AS destination,
               s.departure_date, s.departure_time, b.bus_name, o.operator_name,
               (SELECT GROUP_CONCAT(x.seat_number ORDER BY x.seat_number) FROM booking_seats x WHERE x.booking_id = bk.id) AS seats
          FROM bookings bk
          JOIN users u ON u.id = bk.user_id
          JOIN schedules s ON s.id = bk.schedule_id
          JOIN buses b ON b.id = s.bus_id
          JOIN transport_operators o ON o.id = b.operator_id""" + _ROUTE_JOIN
    params: dict = {"lim": limit}
    if status in ("CONFIRMED", "CANCELLED", "COMPLETED"):
        sql += " WHERE bk.booking_status = :st"
        params["st"] = status
    sql += " ORDER BY bk.booked_at DESC, bk.id DESC LIMIT :lim"
    return rows_to_dicts(conn.execute(text(sql), params).mappings().all())


def list_users(conn: Connection, limit: int = 200) -> list[dict]:
    sql = """SELECT u.id, u.full_name, u.phone_number, u.role, u.created_at,
                    COUNT(bk.id) AS bookings
               FROM users u LEFT JOIN bookings bk ON bk.user_id = u.id
              GROUP BY u.id, u.full_name, u.phone_number, u.role, u.created_at
              ORDER BY u.created_at DESC LIMIT :lim"""
    return rows_to_dicts(conn.execute(text(sql), {"lim": limit}).mappings().all())


def list_districts(conn: Connection) -> list[dict]:
    sql = """SELECT d.id, d.district_name, d.slug, COUNT(DISTINCT st.id) AS stations
               FROM districts d LEFT JOIN stations st ON st.district_id = d.id
              GROUP BY d.id, d.district_name, d.slug ORDER BY d.id"""
    return rows_to_dicts(conn.execute(text(sql)).mappings().all())


def list_operators(conn: Connection) -> list[dict]:
    sql = """SELECT o.id, o.operator_name, o.contact_phone, o.contact_email, COUNT(b.id) AS buses
               FROM transport_operators o LEFT JOIN buses b ON b.operator_id = o.id
              GROUP BY o.id, o.operator_name, o.contact_phone, o.contact_email ORDER BY o.operator_name"""
    return rows_to_dicts(conn.execute(text(sql)).mappings().all())


def list_routes(conn: Connection) -> list[dict]:
    sql = """SELECT r.id, sd.district_name AS origin, dd.district_name AS destination,
                    r.distance_km, r.estimated_duration_minutes AS duration_minutes
               FROM routes r
               JOIN stations ss ON ss.id = r.source_station_id JOIN districts sd ON sd.id = ss.district_id
               JOIN stations ds ON ds.id = r.destination_station_id JOIN districts dd ON dd.id = ds.district_id
              ORDER BY sd.district_name, dd.district_name"""
    return rows_to_dicts(conn.execute(text(sql)).mappings().all())


def list_buses(conn: Connection) -> list[dict]:
    sql = """SELECT b.id, b.operator_id, o.operator_name, b.bus_name, b.bus_type, b.registration_number,
                    b.total_seats, b.is_active, COUNT(s.id) AS schedules
               FROM buses b JOIN transport_operators o ON o.id = b.operator_id
               LEFT JOIN schedules s ON s.bus_id = b.id
              GROUP BY b.id, b.operator_id, o.operator_name, b.bus_name, b.bus_type,
                       b.registration_number, b.total_seats, b.is_active
              ORDER BY o.operator_name, b.bus_name"""
    return rows_to_dicts(conn.execute(text(sql)).mappings().all())


def list_schedules(conn: Connection, limit: int = 200, upcoming_only: bool = True) -> list[dict]:
    sql = SCHEDULE_SELECT
    params: dict = {"lim": limit}
    if upcoming_only:
        sql += " WHERE s.departure_date >= :today"
        params["today"] = now_bd_naive().date()
    sql += " ORDER BY s.departure_date, s.departure_time, s.id LIMIT :lim"
    return [decorate_schedule(row_to_dict(r)) for r in conn.execute(text(sql), params).mappings().all()]


def list_audit_logs(conn: Connection, limit: int = 200) -> list[dict]:
    sql = """SELECT a.id, a.action, a.details, a.created_at, a.booking_id, a.user_id,
                    bk.booking_reference, u.full_name AS user_name
               FROM audit_logs a
               LEFT JOIN bookings bk ON bk.id = a.booking_id
               LEFT JOIN users u ON u.id = a.user_id
              ORDER BY a.id DESC LIMIT :lim"""
    return rows_to_dicts(conn.execute(text(sql), {"lim": limit}).mappings().all())


def list_low_seat_alerts(conn: Connection, open_only: bool = False, limit: int = 100) -> list[dict]:
    sql = """SELECT a.id, a.schedule_id, a.available_seats, a.threshold, a.alert_message,
                    a.created_at, a.resolved_at,
                    sd.district_name AS origin, dd.district_name AS destination,
                    s.departure_date, s.departure_time, b.bus_name
               FROM low_seat_alerts a
               JOIN schedules s ON s.id = a.schedule_id
               JOIN buses b ON b.id = s.bus_id""" + _ROUTE_JOIN
    if open_only:
        sql += " WHERE a.resolved_at IS NULL"
    sql += " ORDER BY (a.resolved_at IS NULL) DESC, a.created_at DESC LIMIT :lim"
    return rows_to_dicts(conn.execute(text(sql), {"lim": limit}).mappings().all())
