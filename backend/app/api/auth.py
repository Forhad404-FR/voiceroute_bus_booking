import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.api.deps import CSRF_COOKIE, COOKIE_NAME, conn_dep, csrf_protect, current_user, engine_dep
from app.core import ratelimit
from app.core.config import get_settings
from app.core.security import burn_password_check, create_access_token, hash_password, verify_password
from app.schemas.models import LoginIn, RegisterIn

router = APIRouter(prefix="/api/auth", tags=["auth"])

REMEMBER_MINUTES = 60 * 24 * 30  # 30 days when "Remember me" is ticked


def _public(user: dict) -> dict:
    return {"id": user["id"], "full_name": user["full_name"], "phone_number": user["phone_number"], "role": user["role"]}


def _set_session(response: Response, user_id: int, remember: bool) -> None:
    s = get_settings()
    minutes = min(s.access_token_expire_minutes, REMEMBER_MINUTES) if remember else min(s.access_token_expire_minutes, 720)
    token = create_access_token(user_id, s.jwt_secret_key, minutes)
    common = dict(httponly=True, secure=s.is_production, samesite="lax", path="/")
    # "Remember me": persistent cookie (max_age). Otherwise a session cookie that ends with the browser.
    response.set_cookie(COOKIE_NAME, token, max_age=minutes * 60 if remember else None, **common)
    response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(24), max_age=minutes * 60 if remember else None,
                        httponly=False, secure=s.is_production, samesite="lax", path="/")


@router.post("/register", status_code=201)
def register(body: RegisterIn, response: Response, engine=Depends(engine_dep)):
    pw_hash = hash_password(body.password)
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("INSERT INTO users (full_name, phone_number, password_hash, role) VALUES (:n, :p, :h, 'USER')"),
                {"n": body.full_name, "p": body.phone_number, "h": pw_hash},
            )
            user_id = res.lastrowid
    except IntegrityError:
        raise HTTPException(status_code=409, detail="This phone number is already registered.") from None
    _set_session(response, user_id, body.remember_me)
    return {"user": {"id": user_id, "full_name": body.full_name, "phone_number": body.phone_number, "role": "USER"}}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, conn: Connection = Depends(conn_dep)):
    key = f"{request.client.host if request.client else 'unknown'}:{body.phone_number}"
    if ratelimit.is_blocked(key):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please wait a few minutes and try again.")
    row = conn.execute(
        text("SELECT id, full_name, phone_number, role, password_hash FROM users WHERE phone_number = :p"),
        {"p": body.phone_number},
    ).mappings().first()
    if not row:
        burn_password_check(body.password)
        ratelimit.record_failure(key)
        raise HTTPException(status_code=401, detail="Incorrect phone number or password.")
    if not verify_password(body.password, row["password_hash"]):
        ratelimit.record_failure(key)
        raise HTTPException(status_code=401, detail="Incorrect phone number or password.")
    ratelimit.reset(key)
    _set_session(response, row["id"], body.remember_me)
    return {"user": _public(dict(row))}


@router.post("/logout", dependencies=[Depends(csrf_protect)])
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"message": "Logged out."}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"user": _public(user)}
