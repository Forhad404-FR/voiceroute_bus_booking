"""Repeatable, non-destructive database initialisation.

    python -m app.database.init_db            # schema + triggers + seed + schedules
    python -m app.database.init_db --only triggers

Every SQL file is idempotent (CREATE ... IF NOT EXISTS, INSERT IGNORE, DROP TRIGGER IF EXISTS +
CREATE TRIGGER). Nothing here deletes or overwrites business data.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from app.database.sqlsplit import split_sql

ORDER = ["schema", "triggers", "seed", "generate_schedules"]


def sql_dir() -> Path:
    here = Path(__file__).resolve()
    for cand in (here.parents[3] / "database", Path("/app/database"), Path.cwd() / "database", Path.cwd().parent / "database"):
        if (cand / "schema.sql").exists():
            return cand
    raise FileNotFoundError("Could not locate the database/ folder containing schema.sql.")


def run_file(engine, path: Path) -> int:
    statements = split_sql(path.read_text(encoding="utf-8"))
    with engine.connect() as conn:
        for stmt in statements:
            conn.exec_driver_sql(stmt)
        conn.commit()
    return len(statements)


def verify(engine) -> dict:
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
        districts = conn.execute(text("SELECT COUNT(*) FROM districts")).scalar()
        triggers = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = DATABASE()")).scalar()
    return {"mysql_version": version, "districts": districts, "triggers": triggers}


def init_database(engine, only: list[str] | None = None, log=print) -> dict:
    base = sql_dir()
    for name in (only or ORDER):
        count = run_file(engine, base / f"{name}.sql")
        log(f"  ran {name}.sql ({count} statements)")
    info = verify(engine)
    if (only is None or "seed" in only) and info["districts"] != 30:
        raise RuntimeError(f"Expected exactly 30 districts but found {info['districts']}.")
    return info


def main() -> int:
    from app.core.config import ConfigError
    from app.database.session import get_engine

    parser = argparse.ArgumentParser(description="Initialise the VoiceRoute MySQL database (safe to re-run).")
    parser.add_argument("--only", nargs="+", choices=ORDER, help="run only these SQL files")
    args = parser.parse_args()
    try:
        engine = get_engine()
        print("Initialising database ...")
        info = init_database(engine, args.only)
    except ConfigError as exc:
        print(f"CONFIGURATION ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # never print the URL / credentials
        print(f"DATABASE ERROR: {type(exc).__name__}: {str(exc)[:300]}", file=sys.stderr)
        return 1
    print(f"Done. MySQL {info['mysql_version']}, districts={info['districts']}, triggers={info['triggers']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
