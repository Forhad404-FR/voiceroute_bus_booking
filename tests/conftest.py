import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Integration tests run only when a dedicated, empty MySQL 8 test database is provided.
TEST_DB = os.getenv("TEST_DATABASE_URL")
if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-automated-tests-only-0123456789")
    os.environ["APP_ENV"] = "development"
