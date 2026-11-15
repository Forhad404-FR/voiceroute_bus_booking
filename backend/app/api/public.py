from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Connection

from app.api.deps import conn_dep
from app.core.timeutil import today_bd
from app.services import catalog

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/districts")
def districts(conn: Connection = Depends(conn_dep)):
    return {"districts": catalog.list_districts(conn)}


@router.get("/districts/search")
def districts_search(q: str = Query("", max_length=60), exclude: str | None = Query(None, max_length=60),
                     conn: Connection = Depends(conn_dep)):
    return {"query": q, "districts": catalog.search_districts(conn, q, exclude)}


@router.get("/routes/parse")
def routes_parse(q: str = Query(..., min_length=1, max_length=200), conn: Connection = Depends(conn_dep)):
    return catalog.parse_route(conn, q)


@router.get("/routes/popular")
def routes_popular(limit: int = Query(8, ge=1, le=20), conn: Connection = Depends(conn_dep)):
    return {"routes": catalog.popular_routes(conn, limit)}


def _resolve_pair(conn: Connection, origin: str, destination: str) -> tuple[str, str]:
    o = catalog.canonical_district(conn, origin)
    d = catalog.canonical_district(conn, destination)
    if not o:
        raise HTTPException(status_code=422, detail="Unknown origin district.")
    if not d:
        raise HTTPException(status_code=422, detail="Unknown destination district.")
    if o == d:
        raise HTTPException(status_code=422, detail="Origin and destination must be different districts.")
    return o, d


@router.get("/routes/search")
def routes_search(origin: str = Query(..., max_length=60), destination: str = Query(..., max_length=60),
                  conn: Connection = Depends(conn_dep)):
    o, d = _resolve_pair(conn, origin, destination)
    return catalog.route_search(conn, o, d)


@router.get("/schedules/search")
def schedules_search(origin: str = Query(..., max_length=60), destination: str = Query(..., max_length=60),
                     date: date = Query(...), sort: str = Query("departure", pattern="^(departure|price)$"),
                     bus_type: str | None = Query(None, pattern="^(AC|NON_AC)$"),
                     only_available: bool = False, conn: Connection = Depends(conn_dep)):
    o, d = _resolve_pair(conn, origin, destination)
    if date < today_bd():
        raise HTTPException(status_code=422, detail="Journey date cannot be in the past.")
    info = catalog.route_search(conn, o, d)
    schedules = catalog.search_schedules(conn, o, d, date, sort, bus_type, only_available) if info["direct"] else []
    return {**info, "date": date.isoformat(), "schedules": schedules, "sample_data": True}


@router.get("/schedules/{schedule_id}")
def schedule_detail(schedule_id: int, conn: Connection = Depends(conn_dep)):
    s = catalog.get_schedule(conn, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found.")
    return {"schedule": s}


@router.get("/schedules/{schedule_id}/seats")
def schedule_seats(schedule_id: int, conn: Connection = Depends(conn_dep)):
    data = catalog.seat_map(conn, schedule_id)
    if not data:
        raise HTTPException(status_code=404, detail="Schedule not found.")
    return data
