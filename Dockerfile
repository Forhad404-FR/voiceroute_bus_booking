# syntax=docker/dockerfile:1
# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json ./
# `npm install` (not `npm ci`) because no lockfile ships in the ZIP; commit the generated package-lock.json afterwards.
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: FastAPI runtime that also serves the built frontend ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY backend/app ./app
COPY database ./database
COPY --from=frontend /build/dist ./app/static
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
# Render injects $PORT. Binds 0.0.0.0. No localhost anywhere in production config.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
