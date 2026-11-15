"""SQLAlchemy engine factory. One engine per process; connections come from a pool."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import build_engine_config, get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url, connect_args = build_engine_config(settings.database_url, settings.database_ssl_ca)
        _engine = create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=280,
            pool_size=5,
            max_overflow=5,
            future=True,
        )
    return _engine


def set_engine(engine: Engine) -> None:
    """Used by the test-suite to inject a test database engine."""
    global _engine
    _engine = engine
