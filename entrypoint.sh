#!/bin/bash
set -e

# ============================================
# MEDIAKEEPER — Single Container Entrypoint
# 1. Generate the PG password on first launch
# 2. Initialise the PG cluster if needed
# 3. Start PostgreSQL
# 4. Launch Uvicorn (FastAPI + static files)
# ============================================

DATA_DIR="/data"
PG_DATA="$DATA_DIR/pg"
PG_PWD_FILE="$DATA_DIR/.pg_password"
PG_LOG="$DATA_DIR/logs/postgresql.log"
PG_BIN="/usr/lib/postgresql/16/bin"

# ---- 0. Remap mkuser UID/GID if PUID/PGID are set ----
PUID=${PUID:-0}
PGID=${PGID:-0}
if [ "$PUID" -ne 0 ]; then
    echo ">> Remapping mkuser UID -> $PUID / users GID -> $PGID"
    # Make sure mkuser has a valid shell so usermod accepts it
    sed -i 's|mkuser:/usr/sbin/nologin|mkuser:/bin/bash|' /etc/passwd 2>/dev/null || true
    groupmod -o -g "$PGID" users 2>/dev/null || true
    usermod -o -u "$PUID" -g "$PGID" -s /bin/bash mkuser 2>/dev/null || true
    # Confirm the change actually applied
    ACTUAL_UID=$(id -u mkuser 2>/dev/null || echo "?")
    echo ">> mkuser effective UID: $ACTUAL_UID (expected: $PUID)"
    chown -R mkuser:users /app/backend 2>/dev/null || true
    # Fix permissions on /data files still owned by the old UID
    chown mkuser:users /data/.jwt_secret /data/.pg_password 2>/dev/null || true
    chmod 600 /data/.jwt_secret /data/.pg_password 2>/dev/null || true
    # Re-chown the /data root so mkuser can create new subdirs (avatars,
    # future /data/* targets). /data/pg is re-chowned to postgres below.
    chown mkuser:users /data 2>/dev/null || true
    chown -R mkuser:users /data/logs /data/backups 2>/dev/null || true
fi

# ---- 0b. Persistent dirs that must exist before first use ----
# Created here (not only in the Dockerfile) so a fresh /data — a named
# volume OR a bind-mount to an empty host dir — has them on boot, without a
# manual ``docker exec mkdir`` from the operator. pg is re-owned to postgres
# and logs/backups to mkuser by the steps further down; initdb sets pg's mode.
mkdir -p /data/avatars /data/pg /data/logs /data/backups 2>/dev/null || true
chown mkuser:users /data/avatars 2>/dev/null || true
chmod 750 /data/avatars 2>/dev/null || true

# ---- 1. Auto-generated PostgreSQL password ----
if [ ! -f "$PG_PWD_FILE" ]; then
    echo ">> First launch: generating the PostgreSQL password..."
    PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "$PG_PASSWORD" > "$PG_PWD_FILE"
    chmod 600 "$PG_PWD_FILE"
    chown mkuser:users "$PG_PWD_FILE"
fi

PG_PASSWORD=$(cat "$PG_PWD_FILE")

# ---- 1b. Auto-generated JWT secret if none is provided ----
JWT_SECRET_FILE="$DATA_DIR/.jwt_secret"
if [ -z "$JWT_SECRET_KEY" ] && [ ! -f "$JWT_SECRET_FILE" ]; then
    echo ">> Auto-generating the JWT secret..."
    python3 -c "import secrets; print(secrets.token_urlsafe(64))" > "$JWT_SECRET_FILE"
    chmod 600 "$JWT_SECRET_FILE"
    chown mkuser:users "$JWT_SECRET_FILE"
fi

# ---- 1c. Fernet key for sensitive settings (API keys, webhooks) ----
ENCRYPTION_KEY_FILE="$DATA_DIR/.encryption_key"
if [ -z "$MEDIAKEEPER_ENCRYPTION_KEY" ] && [ ! -f "$ENCRYPTION_KEY_FILE" ]; then
    echo ">> Auto-generating the Fernet encryption key..."
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > "$ENCRYPTION_KEY_FILE"
    chmod 600 "$ENCRYPTION_KEY_FILE"
    chown mkuser:users "$ENCRYPTION_KEY_FILE"
fi

# ---- 2. Initialise the PG cluster if missing ----
if [ ! -f "$PG_DATA/PG_VERSION" ]; then
    echo ">> Initialising the PostgreSQL cluster..."
    chown -R postgres:postgres "$PG_DATA"
    su - postgres -c "$PG_BIN/initdb -D $PG_DATA --encoding=UTF8 --locale=C"

    # Configure authentication
    echo "host all all 127.0.0.1/32 md5" >> "$PG_DATA/pg_hba.conf"
    echo "local all all md5" >> "$PG_DATA/pg_hba.conf"

    # Listen on localhost only
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '127.0.0.1'/" "$PG_DATA/postgresql.conf"
    sed -i "s/#port = 5432/port = 5432/" "$PG_DATA/postgresql.conf"

    # Start temporarily to create the user + db
    touch "$PG_LOG"
    chown postgres:postgres "$PG_LOG"
    su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA -l $PG_LOG start -w"

    su - postgres -c "$PG_BIN/psql -c \"CREATE USER mediakeeper WITH PASSWORD '$PG_PASSWORD';\""
    su - postgres -c "$PG_BIN/psql -c \"CREATE DATABASE mediakeeper_db OWNER mediakeeper;\""
    su - postgres -c "$PG_BIN/psql -c \"GRANT ALL PRIVILEGES ON DATABASE mediakeeper_db TO mediakeeper;\""

    su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA stop -w"
    echo ">> PostgreSQL cluster initialised."
fi

# ---- 3. Start PostgreSQL ----
chown -R postgres:postgres "$PG_DATA"
# Clean up any leftover PID file (previous crash)
rm -f "$PG_DATA/postmaster.pid"
# The PG log file must be writable by the postgres user
touch "$PG_LOG"
chown postgres:postgres "$PG_LOG"
echo ">> Starting PostgreSQL..."
su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA -l $PG_LOG start -w"

# Wait until PG is ready
for i in $(seq 1 30); do
    if su - postgres -c "$PG_BIN/pg_isready -h 127.0.0.1 -p 5432" > /dev/null 2>&1; then
        echo ">> PostgreSQL ready."
        break
    fi
    sleep 1
done

# ---- 4. Environment variables for FastAPI ----
export DATABASE_URL="postgresql://mediakeeper:${PG_PASSWORD}@127.0.0.1:5432/mediakeeper_db"

# Logs dir permissions
chown -R mkuser:users /data/logs /data/backups

# ---- 4b. Apply Alembic migrations (idempotent) ----
# Each Alembic migration is written as a no-op when its target table/column
# already exists (``if ... not in tables`` guards), so re-running
# ``upgrade head`` on every boot is safe and guarantees that any newly
# shipped migration is picked up at the next rebuild.
echo ">> Applying Alembic migrations..."
su -s /bin/bash mkuser -c "cd /app/backend && alembic upgrade head" || {
    echo ">> ⚠  Alembic migrations failed — aborting."
    exit 1
}

# ---- 5. Launch Uvicorn ----
echo ">> Starting MediaKeeper..."
MK_DEBUG="${MK_DEBUG:-false}"
MK_SEPARATE_BACKGROUND_WORKER="${MK_SEPARATE_BACKGROUND_WORKER:-true}"

terminate_child() {
    local pid="$1"
    if [ -z "$pid" ]; then
        return
    fi
    pkill -TERM -P "$pid" 2>/dev/null || true
    kill -TERM "$pid" 2>/dev/null || true
}

shutdown_all() {
    terminate_child "$WEB_PID"
    terminate_child "$WORKER_PID"
    wait "$WEB_PID" "$WORKER_PID" 2>/dev/null || true
    su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA stop -m fast" >/dev/null 2>&1 || true
}

if [ "$MK_DEBUG" = "true" ]; then
    echo ">> DEBUG mode enabled (reload + verbose logs)"
    exec su -s /bin/bash mkuser -c "cd /app/backend && exec env MK_PROCESS_ROLE=combined uvicorn main:app --host 0.0.0.0 --port 8888 --reload --log-level debug"
else
    if [ "$MK_SEPARATE_BACKGROUND_WORKER" = "true" ]; then
        echo ">> Production mode: web API / background tasks split"
        trap shutdown_all INT TERM

        su -s /bin/bash mkuser -c "cd /app/backend && exec env MK_PROCESS_ROLE=worker python run_worker.py" &
        WORKER_PID=$!

        su -s /bin/bash mkuser -c "cd /app/backend && exec env MK_PROCESS_ROLE=web uvicorn main:app --host 0.0.0.0 --port 8888 --workers 1" &
        WEB_PID=$!

        wait -n "$WEB_PID" "$WORKER_PID"
        STATUS=$?
        shutdown_all
        exit "$STATUS"
    fi

    exec su -s /bin/bash mkuser -c "cd /app/backend && exec env MK_PROCESS_ROLE=combined uvicorn main:app --host 0.0.0.0 --port 8888 --workers 1"
fi
