"""Seat numbering and layout helpers (pure). Seats are stored as integers 1..total_seats;
the label (A1, A2 | A3, A4, B1, ...) is derived: four seats per row, aisle after the 2nd."""
from __future__ import annotations

SEATS_PER_ROW = 4
MAX_SEATS_PER_BOOKING = 6


def seat_label(number: int) -> str:
    row = (number - 1) // SEATS_PER_ROW
    col = (number - 1) % SEATS_PER_ROW + 1
    return f"{chr(65 + row)}{col}"


def build_layout(total_seats: int, booked: set[int]) -> list[dict]:
    seats = []
    for n in range(1, total_seats + 1):
        seats.append({
            "seat_number": n,
            "label": seat_label(n),
            "row": (n - 1) // SEATS_PER_ROW,
            "col": (n - 1) % SEATS_PER_ROW,
            "status": "BOOKED" if n in booked else "AVAILABLE",
        })
    return seats


def validate_seat_selection(seats: list[int], total_seats: int) -> str | None:
    """Return an error message or None."""
    if not seats:
        return "Select at least one seat."
    if len(seats) > MAX_SEATS_PER_BOOKING:
        return f"You can book at most {MAX_SEATS_PER_BOOKING} seats at a time."
    if len(set(seats)) != len(seats):
        return "Duplicate seats in request."
    if any((not isinstance(s, int)) or isinstance(s, bool) or s < 1 or s > total_seats for s in seats):
        return "One or more seat numbers do not exist on this bus."
    return None
