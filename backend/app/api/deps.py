"""Shared FastAPI dependencies: DB access, authentication, authorization, CSRF."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.database.session import get_engine

COOKIE_NAME = "vr_session"
CSRF_COOKIE = "vr_csrf"
CSRF_HEADER = "x-csrf-token"


def engine_dep() -> Engine:
    return get_engine()


def conn_dep():
    with get_engine().connect() as conn:
        yield conn


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def current_user(request: Request, conn: Connection = Depends(conn_dep)) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Please log in to continue.")
    try:
        payload = decode_access_token(token, get_settings().jwt_secret_key)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.") from None
    row = conn.execute(
        text("SELECT id, full_name, phone_number, role, created_at FROM users WHERE id = :id"), {"id": user_id}
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=401, detail="Account not found. Please log in again.")
    return dict(row)


def admin_user(user: dict = Depends(current_user)) -> dict:
    """Authorization is re-checked against the database role on every admin request."""
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


def csrf_protect(request: Request) -> None:
    """Double-submit-cookie CSRF check for state-changing requests authenticated by cookie.
    Requests that authenticate with an Authorization header (not auto-sent by browsers) skip it."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if request.headers.get("authorization"):
        return
    if request.cookies.get(COOKIE_NAME):
        cookie = request.cookies.get(CSRF_COOKIE)
        header = request.headers.get(CSRF_HEADER)
        if not cookie or not header or cookie != header:
            raise HTTPException(status_code=403, detail="CSRF validation failed. Refresh the page and try again.")
