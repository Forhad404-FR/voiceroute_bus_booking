"""First-admin creation. Credentials come from environment variables / CLI prompt only."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.security import hash_password, normalize_phone, validate_password_strength


def create_admin(engine: Engine, name: str, phone: str, password: str, promote_existing: bool = True) -> str:
    phone = normalize_phone(phone)
    problem = validate_password_strength(password)
    if problem:
        raise ValueError(problem)
    name = " ".join(name.split()) or "Administrator"
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id, role FROM users WHERE phone_number = :p FOR UPDATE"), {"p": phone}).first()
        if row:
            if row[1] == "ADMIN":
                return "exists"
            if not promote_existing:
                raise ValueError("A normal user with this phone number already exists.")
            conn.execute(text("UPDATE users SET role = 'ADMIN' WHERE id = :id"), {"id": row[0]})
            return "promoted"
        conn.execute(
            text("INSERT INTO users (full_name, phone_number, password_hash, role) VALUES (:n, :p, :h, 'ADMIN')"),
            {"n": name, "p": phone, "h": hash_password(password)},
        )
        return "created"
