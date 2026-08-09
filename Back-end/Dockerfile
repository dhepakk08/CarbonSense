# backend/Dockerfile
# ------------------------------------------------------------
# CarbonSense backend image — Flask API served by gunicorn.
# Build context: ./backend
# ------------------------------------------------------------

FROM python:3.11-slim

# Prevent .pyc files and force stdout/stderr to be unbuffered
# (so `docker logs` shows Flask/gunicorn output immediately)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps: curl for the HEALTHCHECK below, sqlite3 CLI for
# debugging the database file from inside the container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer is cached unless
# requirements.txt actually changes (faster rebuilds).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the backend source
COPY . .

EXPOSE 5000

# Lets `docker ps` / `docker compose ps` report container health,
# and gives Compose something to wait on with `depends_on: condition: service_healthy`.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# gunicorn = production-grade WSGI server (the Flask dev server used
# in `python app.py` is not meant to be exposed from a container).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "app:app"]
