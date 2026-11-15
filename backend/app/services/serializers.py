"""Convert database rows into JSON-friendly dictionaries."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal


def _fmt_time(value) -> str:
    if isinstance(value, timedelta):
        total = int(value.total_seconds()) % 86400
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)


def to_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):  # DB timestamps are stored in UTC
        return value.replace(microsecond=0).isoformat() + ("Z" if value.tzinfo is None else "")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (time, timedelta)):
        return _fmt_time(value)
    return value


def row_to_dict(row) -> dict:
    return {k: to_jsonable(v) for k, v in dict(row).items()}


def rows_to_dicts(rows) -> list[dict]:
    return [row_to_dict(r) for r in rows]
