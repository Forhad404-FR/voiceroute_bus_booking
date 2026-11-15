"""Bangladesh time helpers. Bangladesh has no DST, so a fixed UTC+6 offset is exact.
The database stores created/booked timestamps in UTC; departures are Bangladesh local time."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

BD_TZ = timezone(timedelta(hours=6))


def now_bd() -> datetime:
    return datetime.now(BD_TZ)


def now_bd_naive() -> datetime:
    """Current Bangladesh wall-clock time without tzinfo (matches DATE/TIME columns)."""
    return now_bd().replace(tzinfo=None)


def today_bd() -> date:
    return now_bd().date()


def departure_dt(dep_date: date, dep_time) -> datetime:
    """Combine a DATE and a TIME (PyMySQL returns TIME as timedelta) into a naive datetime."""
    if isinstance(dep_time, timedelta):
        return datetime.combine(dep_date, datetime.min.time()) + dep_time
    return datetime.combine(dep_date, dep_time)
