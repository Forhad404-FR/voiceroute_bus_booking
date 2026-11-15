from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.api.deps import admin_user, conn_dep, csrf_protect, engine_dep
from app.schemas.models import BusIn, ScheduleIn, ScheduleUpdateIn
from app.services import admin as svc

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_user)])
write = [Depends(csrf_protect)]


@router.get("/dashboard")
def dashboard(conn: Connection = Depends(conn_dep)):
    return svc.dashboard(conn)


@router.get("/bookings")
def bookings(status: str | None = Query(None, pattern="^(CONFIRMED|CANCELLED|COMPLETED)$"),
             limit: int = Query(100, ge=1, le=500), conn: Connection = Depends(conn_dep)):
    return {"bookings": svc.list_bookings(conn, limit, status)}


@router.get("/users")
def users(conn: Connection = Depends(conn_dep)):
    return {"users": svc.list_users(conn)}


@router.get("/districts")
def districts(conn: Connection = Depends(conn_dep)):
    return {"districts": svc.list_districts(conn)}


@router.get("/operators")
def operators(conn: Connection = Depends(conn_dep)):
    return {"operators": svc.list_operators(conn)}


@router.get("/routes")
def routes(conn: Connection = Depends(conn_dep)):
    return {"routes": svc.list_routes(conn)}


@router.get("/buses")
def buses(conn: Connection = Depends(conn_dep)):
    return {"buses": svc.list_buses(conn)}


@router.post("/buses", status_code=201, dependencies=write)
def create_bus(body: BusIn, engine=Depends(engine_dep)):
    try:
        with engine.begin() as conn:
            res = conn.execute(text(
                "INSERT INTO buses (operator_id, bus_name, bus_type, registration_number, total_seats, is_active) "
                "VALUES (:o, :n, :t, :r, :s, :a)"),
                {"o": body.operator_id, "n": body.bus_name, "t": body.bus_type, "r": body.registration_number.upper(),
                 "s": body.total_seats, "a": int(body.is_active)})
            bus_id = res.lastrowid
    except IntegrityError as e:
        msg = "Registration number already exists." if "uq_buses_registration" in str(e.orig) else "Unknown operator."
        raise HTTPException(status_code=409, detail=msg) from None
    return {"id": bus_id}


@router.put("/buses/{bus_id}", dependencies=write)
def update_bus(bus_id: int, body: BusIn, engine=Depends(engine_dep)):
    try:
        with engine.begin() as conn:
            res = conn.execute(text(
                "UPDATE buses SET operator_id=:o, bus_name=:n, bus_type=:t, registration_number=:r, "
                "total_seats=:s, is_active=:a WHERE id=:id"),
                {"o": body.operator_id, "n": body.bus_name, "t": body.bus_type, "r": body.registration_number.upper(),
                 "s": body.total_seats, "a": int(body.is_active), "id": bus_id})
            exists = conn.execute(text("SELECT 1 FROM buses WHERE id=:id"), {"id": bus_id}).first()
            if not exists:
                raise HTTPException(status_code=404, detail="Bus not found.")
    except IntegrityError as e:
        msg = "Registration number already exists." if "uq_buses_registration" in str(e.orig) else "Unknown operator."
        raise HTTPException(status_code=409, detail=msg) from None
    return {"message": "Bus updated. Existing schedules keep their original seat capacity."}


@router.delete("/buses/{bus_id}", dependencies=write)
def delete_bus(bus_id: int, engine=Depends(engine_dep)):
    """Deletion is blocked by the FOREIGN KEY (ON DELETE RESTRICT) when the bus has schedules,
    which protects booking history. Such buses can be deactivated instead."""
    try:
        with engine.begin() as conn:
            res = conn.execute(text("DELETE FROM buses WHERE id=:id"), {"id": bus_id})
            if res.rowcount == 0:
                raise HTTPException(status_code=404, detail="Bus not found.")
    except IntegrityError:
        raise HTTPException(status_code=409, detail="This bus has schedules, so it cannot be deleted. Deactivate it instead.") from None
    return {"message": "Bus deleted."}


@router.get("/schedules")
def schedules(limit: int = Query(200, ge=1, le=500), upcoming_only: bool = True, conn: Connection = Depends(conn_dep)):
    return {"schedules": svc.list_schedules(conn, limit, upcoming_only)}


@router.post("/schedules", status_code=201, dependencies=write)
def create_schedule(body: ScheduleIn, engine=Depends(engine_dep)):
    try:
        with engine.begin() as conn:
            bus = conn.execute(text("SELECT total_seats FROM buses WHERE id=:id AND is_active=1"), {"id": body.bus_id}).first()
            if not bus:
                raise HTTPException(status_code=422, detail="Bus not found or inactive.")
            res = conn.execute(text(
                "INSERT INTO schedules (bus_id, route_id, departure_date, departure_time, arrival_time, fare, "
                "total_seats, available_seats, status) VALUES (:b, :r, :d, :dt, :at, :f, :s, :s, :st)"),
                {"b": body.bus_id, "r": body.route_id, "d": body.departure_date, "dt": body.departure_time,
                 "at": body.arrival_time, "f": body.fare, "s": bus[0], "st": body.status})
            sid = res.lastrowid
    except IntegrityError as e:
        msg = "This bus already has that departure." if "uq_schedule_departure" in str(e.orig) else "Unknown bus or route."
        raise HTTPException(status_code=409, detail=msg) from None
    return {"id": sid}


@router.put("/schedules/{schedule_id}", dependencies=write)
def update_schedule(schedule_id: int, body: ScheduleUpdateIn, engine=Depends(engine_dep)):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=422, detail="Nothing to update.")
    allowed = {"departure_date", "departure_time", "arrival_time", "fare", "status"}
    sets = ", ".join(f"{k} = :{k}" for k in fields if k in allowed)  # column names come from a fixed allow-list
    try:
        with engine.begin() as conn:
            if not conn.execute(text("SELECT 1 FROM schedules WHERE id=:id FOR UPDATE"), {"id": schedule_id}).first():
                raise HTTPException(status_code=404, detail="Schedule not found.")
            conn.execute(text(f"UPDATE schedules SET {sets} WHERE id = :id"), {**fields, "id": schedule_id})
    except IntegrityError:
        raise HTTPException(status_code=409, detail="This bus already has that departure.") from None
    return {"message": "Schedule updated. Existing bookings keep the fare they were booked at."}


@router.delete("/schedules/{schedule_id}", dependencies=write)
def delete_schedule(schedule_id: int, engine=Depends(engine_dep)):
    try:
        with engine.begin() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM bookings WHERE schedule_id=:id"), {"id": schedule_id}).scalar()
            if n:
                raise HTTPException(status_code=409, detail="This schedule has bookings, so it cannot be deleted. Set it to CANCELLED instead.")
            res = conn.execute(text("DELETE FROM schedules WHERE id=:id"), {"id": schedule_id})
            if res.rowcount == 0:
                raise HTTPException(status_code=404, detail="Schedule not found.")
    except IntegrityError:
        raise HTTPException(status_code=409, detail="This schedule is in use and cannot be deleted.") from None
    return {"message": "Schedule deleted."}


@router.get("/audit-logs")
def audit_logs(limit: int = Query(200, ge=1, le=1000), conn: Connection = Depends(conn_dep)):
    return {"audit_logs": svc.list_audit_logs(conn, limit)}


@router.get("/low-seat-alerts")
def low_seat_alerts(open_only: bool = False, conn: Connection = Depends(conn_dep)):
    return {"alerts": svc.list_low_seat_alerts(conn, open_only)}
