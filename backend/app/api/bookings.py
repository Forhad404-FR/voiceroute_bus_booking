from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import csrf_protect, current_user, engine_dep
from app.schemas.models import BookingIn
from app.services import bookings as svc

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def _wrap(fn, *a):
    try:
        return fn(*a)
    except svc.BookingError as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "seats": e.seats}) from None


@router.post("", status_code=201, dependencies=[Depends(csrf_protect)])
def create(body: BookingIn, user: dict = Depends(current_user), engine=Depends(engine_dep)):
    # user id comes from the verified token only, never from the request body
    return {"booking": _wrap(svc.create_booking, engine, user["id"], body.schedule_id, body.seat_numbers)}


@router.get("/my")
def my_bookings(user: dict = Depends(current_user), engine=Depends(engine_dep)):
    return {"bookings": svc.list_bookings_for_user(engine, user["id"])}


@router.get("/{booking_id}")
def one(booking_id: int, user: dict = Depends(current_user), engine=Depends(engine_dep)):
    return {"booking": _wrap(svc.get_booking_for_user, engine, booking_id, user["id"])}


@router.post("/{booking_id}/cancel", dependencies=[Depends(csrf_protect)])
def cancel(booking_id: int, user: dict = Depends(current_user), engine=Depends(engine_dep)):
    return {"booking": _wrap(svc.cancel_booking, engine, booking_id, user["id"]),
            "message": "Booking cancelled. Your seats have been released."}
