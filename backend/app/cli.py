"""Command-line tools.

    python -m app.cli init-db
    python -m app.cli create-admin            # reads ADMIN_NAME/ADMIN_PHONE/ADMIN_PASSWORD or prompts
    python -m app.cli complete-bookings       # mark past CONFIRMED bookings COMPLETED
    python -m app.cli refresh-schedules       # add sample schedules for the next 30 days
"""
from __future__ import annotations

import getpass
import os
import sys


def main(argv: list[str]) -> int:
    from app.core.config import ConfigError, get_settings
    from app.database.session import get_engine

    cmd = argv[0] if argv else ""
    try:
        get_settings()
        engine = get_engine()
        if cmd == "init-db":
            from app.database.init_db import init_database
            print(init_database(engine))
        elif cmd == "refresh-schedules":
            from app.database.init_db import init_database
            print(init_database(engine, ["generate_schedules"]))
        elif cmd == "create-admin":
            from app.services.bootstrap import create_admin
            s = get_settings()
            name = s.admin_name or input("Admin full name: ")
            phone = s.admin_phone or input("Admin phone (01XXXXXXXXX): ")
            password = s.admin_password or getpass.getpass("Admin password: ")
            print("Admin:", create_admin(engine, name, phone, password))
        elif cmd == "complete-bookings":
            from app.services.bookings import complete_past_bookings
            print("Completed:", complete_past_bookings(engine))
        else:
            print(__doc__)
            return 1
    except ConfigError as exc:
        print(f"CONFIGURATION ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
