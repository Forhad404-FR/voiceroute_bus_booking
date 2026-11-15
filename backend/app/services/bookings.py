"""Transaction-safe booking and cancellation.

Booking workflow (one InnoDB transaction):
  1. BEGIN (engine.begin())
  2. SELECT ... FROM schedules WHERE id=:id FOR UPDATE   -> serialises concurrent bookings
  3. verify status ACTIVE and departure still in the future
  4. validate seat numbers against the schedule's seat count
  5. SELECT ... FROM booking_seats ... FOR UPDATE        -> lock requested seat inventory
  6. verify every seat is free and enough seats remain
  7. INSERT booking (fare computed on the server from schedules.fare, never from the client)
  8. INSERT booking_seats
  9. MySQL trigger trg_bookings_after_insert decrements schedules.available_seats,
     writes the audit log and (via trg_schedules_after_update) raises low-seat alerts
 10. COMMIT   (any error -> ROLLBACK, so seat counts are never left half-updated)
The UNIQUE(schedule_id, active_seat) key is a final database-level guard against double booking.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.security import new_booking_reference
from app.core.timeutil import departure_dt, now_bd_naive
from app.services.seats import seat_label, validate_seat_selection
from app.services.serializers import row_to_dict, rows_to_dicts


class BookingError(Exception):
    def __init__(self, message: str, status_code: int = 400, seats: list[int] | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.seats = seats or []


BOOKING_SELECT = """
SELECT bk.id, bk.booking_reference, bk.user_id, bk.schedule_id, bk.seat_count, bk.total_fare,
       bk.booking_status, bk.booked_at, bk.cancelled_at,
       u.full_name AS passenger_name, u.phone_number,
       s.departure_date, s.departure_time, s.arrival_time, s.fare AS fare_per_seat, s.status AS schedule_status,
       b.bus_name, b.bus_type, o.operator_name,
       sd.district_name AS origin, dd.district_name AS destination,
       ss.station_name AS origin_station, ds.station_name AS destination_station,
       (SELECT GROUP_CONCAT(x.seat_number ORDER BY x.seat_number)
          FROM booking_seats x WHERE x.booking_id = bk.id) AS seat_numbers
  FROM bookings bk
  JOIN users u               ON u.id = bk.user_id
  JOIN schedules s           ON s.id = bk.schedule_id
  JOIN buses b               ON b.id = s.bus_id
  JOIN transport_operators o ON o.id = b.operator_id
  JOIN routes r              ON r.id = s.route_id
  JOIN stations ss           ON ss.id = r.source_station_id
  JOIN districts sd          ON sd.id = ss.district_id
  JOIN stations ds           ON ds.id = r.destination_station_id
  JOIN districts dd          ON dd.id = ds.district_id
"""


def _decorate(d: dict) -> dict:
    nums = [int(x) for x in str(d.get("seat_numbers") or "").split(",") if x]
    d["seat_numbers"] = nums
    d["seat_labels"] = [seat_label(n) for n in nums]
    d["status"] = d["booking_status"]
    d["bus_type_label"] = "AC" if d.get("bus_type") == "AC" else "Non-AC"
    d["is_sample_data"] = True
    dep = departure_dt(
        date.fromisoformat(str(d["departure_date"])),
        datetime.strptime(str(d["departure_time"]), "%H:%M").time(),
    )
    d["can_cancel"] = d["booking_status"] == "CONFIRMED" and dep > now_bd_naive()
    return d


def create_booking(engine: Engine, user_id: int, schedule_id: int, seat_numbers: list[int]) -> dict:
    seats = sorted(seat_numbers)
    try:
        with engine.begin() as conn:  # BEGIN ... COMMIT / ROLLBACK on exception
            sched = conn.execute(
                text("SELECT id, fare, total_seats, available_seats, status, departure_date, departure_time "
                     "FROM schedules WHERE id = :id FOR UPDATE"),
                {"id": schedule_id},
            ).mappings().first()
            if not sched:
                raise BookingError("Schedule not found.", 404)
            if sched["status"] != "ACTIVE":
                raise BookingError("This schedule is no longer available for booking.", 409)
            if departure_dt(sched["departure_date"], sched["departure_time"]) <= now_bd_naive():
                raise BookingError("This bus has already departed.", 409)

            problem = validate_seat_selection(seats, int(sched["total_seats"]))
            if problem:
                raise BookingError(problem, 422)

            taken_rows = conn.execute(
                text("SELECT seat_number FROM booking_seats "
                     "WHERE schedule_id = :id AND seat_status = 'BOOKED' AND seat_number IN :seats FOR UPDATE")
                .bindparams(bindparam("seats", expanding=True)),
                {"id": schedule_id, "seats": seats},
            ).all()
            taken = sorted(r[0] for r in taken_rows)
            if taken:
                raise BookingError(
                    "Seat(s) " + ", ".join(seat_label(n) for n in taken) + " already booked. Please choose other seats.",
                    409, taken)
            if int(sched["available_seats"]) < len(seats):
                raise BookingError("Not enough seats remaining on this bus.", 409)

            fare = Decimal(sched["fare"])
            total = (fare * len(seats)).quantize(Decimal("0.01"))
            booking_id = None
            for _attempt in range(5):  # retry only on an (astronomically unlikely) reference clash
                reference = new_booking_reference()
                try:
                    with conn.begin_nested():
                        res = conn.execute(
                            text("INSERT INTO bookings (booking_reference, user_id, schedule_id, seat_count, total_fare) "
                                 "VALUES (:ref, :uid, :sid, :cnt, :total)"),
                            {"ref": reference, "uid": user_id, "sid": schedule_id, "cnt": len(seats), "total": total},
                        )
                    booking_id = res.lastrowid
                    break
                except IntegrityError as exc:
                    if "booking_reference" in str(exc.orig) or "uq_bookings_reference" in str(exc.orig):
                        continue
                    raise
            if booking_id is None:
                raise BookingError("Could not generate a booking reference. Please retry.", 500)

            conn.execute(
                text("INSERT INTO booking_seats (booking_id, schedule_id, seat_number) VALUES (:b, :s, :n)"),
                [{"b": booking_id, "s": schedule_id, "n": n} for n in seats],
            )
            # trigger trg_bookings_after_insert has now decremented available_seats
    except BookingError:
        raise
    except IntegrityError as exc:
        # UNIQUE(schedule_id, active_seat) fired: a concurrent booking won the seat
        if "uq_schedule_active_seat" in str(exc.orig):
            raise BookingError("One of the seats was just booked by someone else. Please choose again.", 409) from None
        raise BookingError("Booking could not be completed.", 409) from None
    except DBAPIError as exc:
        msg = str(getattr(exc, "orig", exc))
        if "Not enough available seats" in msg:
            raise BookingError("Not enough seats remaining on this bus.", 409) from None
        raise

    return get_booking_for_user(engine, booking_id, user_id)  # type: ignore[arg-type]


def get_booking_for_user(engine: Engine, booking_id: int, user_id: int) -> dict:
    """Ownership is enforced in SQL. A foreign booking id is indistinguishable from a missing one (404)."""
    with engine.connect() as conn:
        row = conn.execute(text(BOOKING_SELECT + " WHERE bk.id = :id AND bk.user_id = :uid"),
                           {"id": booking_id, "uid": user_id}).mappings().first()
    if not row:
        raise BookingError("Booking not found.", 404)
    return _decorate(row_to_dict(row))


def list_bookings_for_user(engine: Engine, user_id: int) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(BOOKING_SELECT + " WHERE bk.user_id = :uid ORDER BY bk.booked_at DESC, bk.id DESC"),
                            {"uid": user_id}).mappings().all()
    return [_decorate(row_to_dict(r)) for r in rows]


def cancel_booking(engine: Engine, booking_id: int, user_id: int) -> dict:
    """Owner-only cancellation. The status UPDATE fires trg_bookings_after_update, which restores
    seats exactly once, releases the seat rows and writes the audit log."""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT bk.id, bk.booking_status, s.departure_date, s.departure_time "
                 "FROM bookings bk JOIN schedules s ON s.id = bk.schedule_id "
                 "WHERE bk.id = :id AND bk.user_id = :uid FOR UPDATE"),
            {"id": booking_id, "uid": user_id},
        ).mappings().first()
        if not row:
            raise BookingError("Booking not found.", 404)
        if row["booking_status"] == "CANCELLED":
            raise BookingError("This booking is already cancelled.", 409)
        if row["booking_status"] != "CONFIRMED":
            raise BookingError("Only confirmed bookings can be cancelled.", 409)
        if departure_dt(row["departure_date"], row["departure_time"]) <= now_bd_naive():
            raise BookingError("This bus has already departed, so the ticket can no longer be cancelled.", 409)
        res = conn.execute(
            text("UPDATE bookings SET booking_status = 'CANCELLED', cancelled_at = UTC_TIMESTAMP() "
                 "WHERE id = :id AND user_id = :uid AND booking_status = 'CONFIRMED'"),
            {"id": booking_id, "uid": user_id},
        )
        if res.rowcount != 1:
            raise BookingError("This booking can no longer be cancelled.", 409)
    return get_booking_for_user(engine, booking_id, user_id)


def complete_past_bookings(engine: Engine) -> int:
    """Mark CONFIRMED bookings whose bus has departed as COMPLETED (trigger writes the audit row)."""
    with engine.begin() as conn:
        res = conn.execute(
            text("UPDATE bookings bk JOIN schedules s ON s.id = bk.schedule_id "
                 "SET bk.booking_status = 'COMPLETED' "
                 "WHERE bk.booking_status = 'CONFIRMED' AND TIMESTAMP(s.departure_date, s.departure_time) < :now"),
            {"now": now_bd_naive()},
        )
        conn.execute(
            text("UPDATE schedules SET status = 'COMPLETED' "
                 "WHERE status = 'ACTIVE' AND TIMESTAMP(departure_date, departure_time) < :now"),
            {"now": now_bd_naive()},
        )
        return res.rowcount or 0
