# VoiceRoute - Voice-Based Transport Enquiry and Booking System

A Database Management Systems course project: a voice-controlled bus enquiry and ticket-booking website for Bangladesh.

> **Academic demonstration only.** Every operator, bus, terminal, distance, fare and schedule is **fictional sample data**
> (operators such as "GreenLine Express" are invented and not affiliated with any real company). Nothing here is a
> verified live timetable, and the system is **not** intended for real ticket sales.

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, React Router, lucide-react, Fetch API |
| Backend | Python, FastAPI, SQLAlchemy (Core, parameterised SQL), PyMySQL, Pydantic, JWT (PyJWT), bcrypt |
| Database | MySQL 8 (InnoDB): FKs, unique keys, indexes, CHECKs, **6 real triggers**, transactions with `SELECT ... FOR UPDATE` |
| Voice | Browser Web Speech API (SpeechRecognition + SpeechSynthesis) - no paid APIs, no desktop libraries |
| Deploy | One Docker image -> one Render Web Service; external (Aiven) MySQL |

## Project layout
```
frontend/    React app (src/pages, components, layouts, services, hooks, context, utils)
backend/app/ FastAPI (api/, core/, database/, services/, schemas/, main.py, cli.py)
database/    schema.sql  triggers.sql  seed.sql  generate_schedules.sql  demo_queries.sql
tests/       test_unit.py (no DB needed)  test_integration.py (needs MySQL 8)
Dockerfile  render.yaml  .env.example  PROJECT_STATUS.md
```

## Database in one minute
11 required tables + `app_settings`: `users, districts, stations, transport_operators, buses, routes, schedules, bookings, booking_seats, audit_logs, low_seat_alerts`.
`routes` link two **stations**, each belonging to a **district** (3NF; no district names are repeated). A **schedule** = one bus on one route on one date.
`schedules.total_seats` is a deliberate snapshot of the bus capacity; `schedules.available_seats` is a counter maintained **only by triggers**.

Triggers (`database/triggers.sql`): `trg_bookings_after_insert` (seats--, audit), `trg_bookings_after_update` (CONFIRMED->CANCELLED: seats++ once, release seat rows, audit),
`trg_schedules_after_update` (open / refresh / resolve low-seat alert, no duplicates; threshold in `app_settings`), plus guard triggers
(`before_insert`, `before_update` make a booking's status final once left CONFIRMED; seat numbers must exist on the bus).
Double-booking is also blocked by the database itself: `booking_seats.active_seat` (generated column) + `UNIQUE(schedule_id, active_seat)`.

Booking transaction (`backend/app/services/bookings.py`): BEGIN -> `SELECT ... FOR UPDATE` on the schedule -> check ACTIVE + future -> validate seats ->
`SELECT ... FOR UPDATE` on the seat rows -> check availability -> INSERT booking (fare computed on the server) -> INSERT seats -> trigger updates counters -> COMMIT (ROLLBACK on any error).

Route network: two hubs, **Dhaka** and **Chattogram**; direct routes hub<->every other district (114 directed routes, no duplicates).
Between two non-hub districts the app says **"No direct bus available"** and suggests the hubs - it never invents a direct schedule.

## Run locally (optional)
```bash
cp .env.example .env            # fill DATABASE_URL (any MySQL 8) and JWT_SECRET_KEY
cd backend && pip install -r requirements.txt
python -m app.cli init-db       # schema + triggers + 30 districts + sample data (safe to re-run)
python -m app.cli create-admin  # prompts, or uses ADMIN_* variables
uvicorn app.main:app --reload   # API on :8000
cd ../frontend && npm install && npm run dev   # UI on :5173 (proxies /api to :8000)
```

---
# Deployment guide (Aiven MySQL + GitHub + Render)

## 1. Create an Aiven MySQL database
1. Sign up at aiven.io -> **Create service** -> **MySQL** -> choose the **Free** plan (or the cheapest) and a region -> **Create**. Wait until it shows *Running*.
2. Open the service **Overview**. You will see Host, Port, User, Password, Database (`defaultdb`) and the **Service URI**.

## 2. Get the connection URL
Copy the **Service URI**. It looks like `mysql://avnadmin:PASSWORD@HOST:PORT/defaultdb?ssl-mode=REQUIRED`.
The app accepts this exact form (it converts it to the PyMySQL driver and handles `ssl-mode`). Treat it as a secret.
Optional but recommended: download the **CA certificate** from the same page and later paste its PEM text into the `DATABASE_SSL_CA` variable to verify the server certificate.

## 3. Environment variables
| Variable | Value |
|---|---|
| `DATABASE_URL` | the Aiven Service URI (required) |
| `JWT_SECRET_KEY` | 32+ random characters (Render can generate it; required) |
| `APP_ENV` | `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days; "Remember me" uses up to 30 days, otherwise a session cookie) |
| `CORS_ORIGINS` | leave **empty** (same-origin deployment) |
| `ADMIN_NAME`, `ADMIN_PHONE`, `ADMIN_PASSWORD` | your first admin (phone like `01712345678`; password >= 8 chars with letters+numbers) |
| `AUTO_BOOTSTRAP` | `true` for the first deploy, then `false` |
| `DATABASE_SSL_CA` | optional Aiven CA PEM |

If `DATABASE_URL` or `JWT_SECRET_KEY` is missing the service **refuses to start** and the Render log shows a clear `Missing required environment variable(s)` message.

## 4-6. Initialise schema, triggers, seed data and the admin account
Pick **one** method. All SQL is idempotent: re-running never deletes or overwrites data.

**Method A (easiest) - automatic on first start.** Set `AUTO_BOOTSTRAP=true` plus the three `ADMIN_*` variables. On start-up the app runs
`schema.sql -> triggers.sql -> seed.sql -> generate_schedules.sql`, verifies exactly 30 districts, and creates the admin. After the first successful deploy set `AUTO_BOOTSTRAP=false` and remove `ADMIN_PASSWORD`.

**Method B - from your computer with the CLI** (needs Python 3.12+):
```bash
cd backend && pip install -r requirements.txt
export DATABASE_URL='mysql://avnadmin:...@host:port/defaultdb?ssl-mode=REQUIRED'
export JWT_SECRET_KEY='any-long-random-string-at-least-32-characters'
python -m app.cli init-db
ADMIN_NAME='Your Name' ADMIN_PHONE='01712345678' ADMIN_PASSWORD='YourStrongPass1' python -m app.cli create-admin
```
**Method C - plain SQL client** (MySQL Workbench / `mysql` CLI): run, in order, `database/schema.sql`, `database/triggers.sql`, `database/seed.sql`, `database/generate_schedules.sql`
(the files use the `DELIMITER` command, which the `mysql` client and Workbench support). Then create the admin with Method B's last command.

**Keeping sample schedules fresh:** schedules are generated for the next 30 days. Re-run `python -m app.cli refresh-schedules` (or redeploy with `AUTO_BOOTSTRAP=true`) to roll the window forward; `python -m app.cli complete-bookings` marks past bookings Completed.

## 7. Push to GitHub
Unzip `VoiceRoute_Complete_Project.zip`, then:
```bash
cd VoiceRoute
git init && git add . && git commit -m "VoiceRoute"
git branch -M main
git remote add origin https://github.com/<you>/voiceroute.git   # create an empty repo first
git push -u origin main
```
`.gitignore` already excludes `.env`, `node_modules` and certificates. **Never commit your real DATABASE_URL.**
(Optional: after the first local `npm install`, commit `frontend/package-lock.json` for reproducible builds.)

## 8-10. Create the Render Web Service and deploy
1. render.com -> **New** -> **Web Service** -> connect GitHub -> pick the repo. (Or **New -> Blueprint** to use `render.yaml`.)
2. Runtime **Docker** (it detects the `Dockerfile`), branch `main`, instance type Free. Health Check Path: `/api/health`.
3. **Environment** tab: add the variables from the table above. Do not put secrets in the repo.
4. **Create Web Service**. Render builds the image (React build -> Python deps -> FastAPI), starts it on `$PORT` and serves site + API from one URL.
5. Watch the logs for `Database connection OK`. If you see `CONFIGURATION ERROR`/`Missing required environment variable`, fix the variable and redeploy.

## 11. Test the deployed site
- `https://<your-app>.onrender.com/api/health` -> `{"status":"ok","database":"connected",...}`
- Open the home page, type `C` in **To District** -> Chattogram, Cumilla, Cox's Bazar, Chandpur; search Dhaka -> Chattogram.
- Register a user, pick seats, confirm, open **My Tickets**, cancel, and check the seat count returns.
- Log in as the admin -> **Admin** menu -> dashboard, audit log, low-seat alerts.
- Refresh on `/my-tickets` (no 404). Voice features need **Chrome/Edge over HTTPS** (Render provides HTTPS) and microphone permission.
- Free Render services sleep after inactivity; the first request may take ~50 s.

## Tests
```bash
pip install -r backend/requirements-dev.txt
pytest tests/test_unit.py                       # no database needed
TEST_DATABASE_URL='mysql+pymysql://user:pass@host:3306/voiceroute_test' pytest tests -v   # full DB/API/trigger/concurrency suite
```
Use a **dedicated empty test database** (never production). See `PROJECT_STATUS.md` for exactly what has and has not been executed.

## Security summary
bcrypt password hashing; JWT in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` when `APP_ENV=production`) with double-submit CSRF token; Remember-me = persistent vs session cookie;
login throttling; owner checks in SQL (`WHERE id=:id AND user_id=:uid`, foreign IDs return 404); admin role re-checked from the database on every `/api/admin/*` call;
fares and availability computed on the server; unpredictable booking references (`VR-` + 10 random chars); parameterised SQL only; generic error messages; credentials only in environment variables.

## Voice commands
Home: tap the mic and say "I want to go from Dhaka to Sylhet" (editable before use). Results: "read results", "book the first bus", "book the cheapest", "show my tickets".
Booking: "book this bus" (speaks a summary), then "confirm" / "no". Tickets: "read my ticket", "cancel booking" (always asks for confirmation). "Stop" and "repeat" work everywhere.
Voice never bypasses login, seat validation, ownership or the confirmation step. Without browser voice support everything works with the normal fields and buttons.
