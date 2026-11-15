"""Application settings, read from environment variables only (never hard-coded).

Missing required configuration raises ConfigError with a clear diagnostic message, so a
mis-configured deployment fails loudly at start-up instead of silently misbehaving.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:  # local development convenience only; production uses real environment variables
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret_key: str
    access_token_expire_minutes: int
    app_env: str
    cors_origins: tuple[str, ...]
    admin_name: str | None
    admin_phone: str | None
    admin_password: str | None
    auto_bootstrap: bool
    database_ssl_ca: str | None

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    missing = [n for n in ("DATABASE_URL", "JWT_SECRET_KEY") if not os.getenv(n, "").strip()]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): " + ", ".join(missing)
            + ". Set them in your Render service (or in a local .env file copied from "
            ".env.example). DATABASE_URL must point to an external MySQL 8 database."
        )
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    secret = os.environ["JWT_SECRET_KEY"].strip()
    if app_env == "production" and len(secret) < 32:
        raise ConfigError("JWT_SECRET_KEY must be at least 32 characters when APP_ENV=production.")
    try:
        minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080") or "10080")
        if minutes < 5:
            raise ValueError
    except ValueError:
        raise ConfigError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer >= 5.") from None
    origins = tuple(o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip())
    return Settings(
        database_url=os.environ["DATABASE_URL"].strip(),
        jwt_secret_key=secret,
        access_token_expire_minutes=minutes,
        app_env=app_env,
        cors_origins=origins,
        admin_name=(os.getenv("ADMIN_NAME") or "").strip() or None,
        admin_phone=(os.getenv("ADMIN_PHONE") or "").strip() or None,
        admin_password=os.getenv("ADMIN_PASSWORD") or None,
        auto_bootstrap=_bool(os.getenv("AUTO_BOOTSTRAP"), False),
        database_ssl_ca=(os.getenv("DATABASE_SSL_CA") or "").strip() or None,
    )


_SSL_MODES_ON = {"required", "verify_ca", "verify_identity", "true", "1"}


def build_engine_config(raw_url: str, ssl_ca: str | None = None) -> tuple[str, dict]:
    """Turn an Aiven/generic MySQL URL into (SQLAlchemy URL, PyMySQL connect_args).

    * mysql://  ->  mysql+pymysql://
    * Aiven's ?ssl-mode=REQUIRED query parameter is not understood by PyMySQL, so it is
      removed and translated into connect_args["ssl"].
    * If ssl_ca (file path or PEM text) is given it is used to verify the server.
      Otherwise, when SSL is requested, the connection is encrypted but the server
      certificate is not verified (documented limitation).
    """
    if not raw_url:
        raise ConfigError("DATABASE_URL is empty.")
    parts = urlsplit(raw_url)
    scheme = parts.scheme.lower()
    if scheme in ("mysql", "mysql+pymysql", "mariadb"):
        scheme = "mysql+pymysql"
    else:
        raise ConfigError(
            "DATABASE_URL must start with mysql:// or mysql+pymysql:// (MySQL 8 is required; "
            "SQLite is not supported)."
        )
    wants_ssl = False
    kept: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower().replace("_", "-") in ("ssl-mode", "sslmode", "ssl"):
            wants_ssl = wants_ssl or value.strip().lower() in _SSL_MODES_ON
        else:
            kept.append((key, value))
    if not any(k.lower() == "charset" for k, _ in kept):
        kept.append(("charset", "utf8mb4"))
    url = urlunsplit((scheme, parts.netloc, parts.path, urlencode(kept), ""))

    connect_args: dict = {"connect_timeout": 15}
    if ssl_ca:
        ca_path = ssl_ca
        if ssl_ca.lstrip().startswith("-----BEGIN"):
            handle = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
            handle.write(ssl_ca.strip() + "\n")
            handle.close()
            ca_path = handle.name
        connect_args["ssl"] = {"ca": ca_path}
    elif wants_ssl:
        connect_args["ssl"] = {"check_hostname": False}
    return url, connect_args
