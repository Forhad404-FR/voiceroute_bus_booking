"""VoiceRoute FastAPI application: JSON API under /api plus the built React app (SPA)."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import admin, auth, bookings, public
from app.core.config import ConfigError, get_settings
from app.database.session import get_engine

log = logging.getLogger("voiceroute")
logging.basicConfig(level=logging.INFO)
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()  # raises ConfigError with a clear message when env vars are missing
    engine = get_engine()
    with engine.connect() as conn:  # fail fast (clear message) if the database is unreachable
        conn.execute(text("SELECT 1"))
    log.info("Database connection OK (env=%s)", settings.app_env)
    if settings.auto_bootstrap:  # opt-in only: idempotent, never deletes data
        from app.database.init_db import init_database
        init_database(engine, log=log.info)
        if settings.admin_phone and settings.admin_password:
            from app.services.bootstrap import create_admin
            log.info("Admin bootstrap: %s", create_admin(engine, settings.admin_name or "Administrator",
                                                         settings.admin_phone, settings.admin_password))
    yield


app = FastAPI(title="VoiceRoute API", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

try:
    _origins = list(get_settings().cors_origins)
except ConfigError:
    _origins = []
if _origins:  # same-origin deployment needs no CORS; only explicitly listed origins are allowed
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "microphone=(self)")
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


@app.exception_handler(HTTPException)
async def http_exc(_: Request, exc: HTTPException):
    detail = exc.detail
    message = detail.get("message") if isinstance(detail, dict) else detail
    body = {"detail": message}
    if isinstance(detail, dict) and detail.get("seats"):
        body["seats"] = detail["seats"]
    return JSONResponse(body, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exc(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    msg = str(first.get("msg", "Invalid input.")).removeprefix("Value error, ")
    loc = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query"))
    return JSONResponse({"detail": f"{loc}: {msg}" if loc and "Password" not in msg and "phone" not in msg.lower() else msg},
                        status_code=422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error: %s", type(exc).__name__)  # details stay in server logs only
    return JSONResponse({"detail": "Something went wrong on the server. Please try again."}, status_code=500)


@app.get("/api/health", tags=["system"])
def health():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "app": "VoiceRoute"}
    except Exception:
        return JSONResponse({"status": "degraded", "database": "unreachable"}, status_code=503)


for r in (auth.router, public.router, bookings.router, admin.router):
    app.include_router(r)


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
def api_not_found(rest: str):
    raise HTTPException(status_code=404, detail="API endpoint not found.")


if STATIC_DIR.joinpath("index.html").exists():
    if STATIC_DIR.joinpath("assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and STATIC_DIR in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")  # React Router deep links survive refresh
else:
    @app.get("/", include_in_schema=False)
    def no_frontend():
        return {"message": "VoiceRoute API is running. The frontend build was not found (backend/app/static)."}
