"""Pydantic request models (input validation)."""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.security import normalize_phone, validate_password_strength


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    phone_number: str
    password: str
    confirm_password: str
    remember_me: bool = True

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)

    @model_validator(mode="after")
    def _check(self):
        problem = validate_password_strength(self.password)
        if problem:
            raise ValueError(problem)
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginIn(BaseModel):
    phone_number: str
    password: str = Field(min_length=1, max_length=200)
    remember_me: bool = True

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)


class BookingIn(BaseModel):
    schedule_id: int = Field(gt=0)
    seat_numbers: list[int] = Field(min_length=1, max_length=6)
    # NOTE: no price / availability fields exist on purpose - the server computes them.


class BusIn(BaseModel):
    operator_id: int = Field(gt=0)
    bus_name: str = Field(min_length=2, max_length=100)
    bus_type: Literal["AC", "NON_AC"]
    registration_number: str = Field(min_length=3, max_length=30)
    total_seats: int = Field(ge=8, le=60)
    is_active: bool = True


class ScheduleIn(BaseModel):
    bus_id: int = Field(gt=0)
    route_id: int = Field(gt=0)
    departure_date: date
    departure_time: time
    arrival_time: time
    fare: Decimal = Field(ge=0, le=100000, max_digits=10, decimal_places=2)
    status: Literal["ACTIVE", "CANCELLED"] = "ACTIVE"


class ScheduleUpdateIn(BaseModel):
    departure_date: date | None = None
    departure_time: time | None = None
    arrival_time: time | None = None
    fare: Decimal | None = Field(default=None, ge=0, le=100000, max_digits=10, decimal_places=2)
    status: Literal["ACTIVE", "CANCELLED"] | None = None
