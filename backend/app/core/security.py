"""Password hashing (bcrypt) and JWT helpers. Heavy imports are lazy so pure logic can be
unit-tested without the full dependency set."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT

JWT_ALGORITHM = "HS256"
_DUMMY_HASH: str | None = None


def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    import bcrypt

    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check when the account does not exist (timing parity)."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_urlsafe(12))
    verify_password(password, _DUMMY_HASH)


def validate_password_strength(password: str) -> str | None:
    """Return an error message, or None when the password is acceptable."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if len(password.encode("utf-8")) > 72:
        return "Password must be at most 72 bytes long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    return None


def create_access_token(user_id: int, secret: str, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    """Raises jwt.PyJWTError for any invalid, expired or tampered token."""
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]})


_PHONE_RE = re.compile(r"^(?:\+?880|0)(1[3-9]\d{8})$")


def normalize_phone(raw: str) -> str:
    """Normalise a Bangladeshi mobile number to the 01XXXXXXXXX form or raise ValueError."""
    cleaned = re.sub(r"[\s\-()]", "", raw or "")
    match = _PHONE_RE.match(cleaned)
    if not match:
        raise ValueError("Enter a valid Bangladeshi mobile number, e.g. 01712345678.")
    return "0" + match.group(1)


_REF_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_booking_reference() -> str:
    """Unpredictable, human-friendly reference such as VR-7K3M9QX2PD (31^10 possibilities)."""
    return "VR-" + "".join(secrets.choice(_REF_ALPHABET) for _ in range(10))
