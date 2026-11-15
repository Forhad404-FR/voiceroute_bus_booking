# PROJECT STATUS (honest report)

## What was actually executed during development
| Check | Result |
|---|---|
| `pytest tests/test_unit.py` (28 tests: 30 districts in seed, autocomplete rules, alias/NL parser, seat rules, password/phone rules, JWT, booking-reference uniqueness, DB-URL translation, missing-env diagnostics, SQL splitter on the real SQL files, static SQL contract) | **28 passed** |
| Python syntax compile of all backend/test files | passed |
| JS/JSX syntax check of all 28 frontend files (TypeScript parser) | 0 errors |
| Static check that every relative import/export in the frontend resolves | 0 problems |

## What was NOT executed (the build environment had no MySQL server, no Docker daemon, and no package-install access)
- **Not run against MySQL:** `schema.sql`, `triggers.sql`, `seed.sql`, `generate_schedules.sql`, `demo_queries.sql`. They were written carefully for MySQL 8.0.13+ but never executed - **run them once and fix any syntax error before submitting.**
- **Not run:** the FastAPI app, `tests/test_integration.py` (17 DB/API/trigger/rollback/concurrency tests - written, skipped without `TEST_DATABASE_URL`).
- **Not run:** `npm install`, `vite build`, the React UI in a browser (no layout, mobile or voice testing), Docker image build, Render deployment, Aiven connection.
- Therefore the following are **implemented but unverified**: triggers, booking transaction/concurrency behaviour, API endpoints, frontend pages and flows, voice features, Docker/Render deployment.

## Implemented (code complete)
Auth (register/login/logout/me, bcrypt, JWT cookie + CSRF, remember-me), 30-district autocomplete + natural-language parser with aliases, two-hub route model with honest "no direct bus" + hub suggestions,
search with sort/filter, seat map, transactional booking, My Tickets (owner-only view/cancel, printable ticket), voice (STT, TTS, commands, confirmations), admin dashboard
(stats, bookings, users, districts, operators, bus CRUD, schedule CRUD, audit log, low-seat alerts), 6 MySQL triggers, demo_queries.sql, Dockerfile, render.yaml, CLI, docs.

## Known limitations
- Single fixed seat layout (4 per row); max 6 seats per booking; no payment, no real operator data, no email/SMS.
- Sample schedules cover 30 days from when they are generated; re-run `refresh-schedules` to extend.
- Login throttling is per-process memory (fine for one instance).
- "Cancel" is allowed until departure; no refunds/fees modelled.
- Aiven TLS: without `DATABASE_SSL_CA` the connection is encrypted but the server certificate is not verified.
- No `package-lock.json` ships (could not be generated offline); the Docker build uses `npm install` with pinned versions. Pinned versions were not re-verified against the registry.
- Speech recognition quality depends on the browser (Chrome/Edge recommended; Firefox lacks SpeechRecognition - the text fallback works).
- Academic demonstration system - not production-ready for commercial ticket sales.
