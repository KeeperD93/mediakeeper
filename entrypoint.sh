#!/bin/bash
set -e

# ============================================
# MEDIAKEEPER — Single Container Entrypoint
# 1. Génère le mot de passe PG au 1er lancement
# 2. Initialise le cluster PG si nécessaire
# 3. Démarre PostgreSQL
# 4. Lance Uvicorn (FastAPI + fichiers statiques)
# ============================================

DATA_DIR="/data"
PG_DATA="$DATA_DIR/pg"
PG_PWD_FILE="$DATA_DIR/.pg_password"
PG_LOG="$DATA_DIR/logs/postgresql.log"
PG_BIN="/usr/lib/postgresql/16/bin"

# ---- 0. Adapter l'UID/GID de mkuser si PUID/PGID sont définis ----
PUID=${PUID:-0}
PGID=${PGID:-0}
if [ "$PUID" -ne 0 ]; then
    echo ">> Adaptation UID mkuser → $PUID / GID users → $PGID"
    # S'assurer que mkuser a un shell valide pour usermod
    sed -i 's|mkuser:/usr/sbin/nologin|mkuser:/bin/bash|' /etc/passwd 2>/dev/null || true
    groupmod -o -g "$PGID" users 2>/dev/null || true
    usermod -o -u "$PUID" -g "$PGID" -s /bin/bash mkuser 2>/dev/null || true
    # Vérifier que le changement a pris effet
    ACTUAL_UID=$(id -u mkuser 2>/dev/null || echo "?")
    echo ">> mkuser UID effectif : $ACTUAL_UID (attendu : $PUID)"
    chown -R mkuser:users /app/backend 2>/dev/null || true
    # Corriger les permissions des fichiers /data appartenant à l'ancien UID
    chown mkuser:users /data/.jwt_secret /data/.pg_password 2>/dev/null || true
    chmod 600 /data/.jwt_secret /data/.pg_password 2>/dev/null || true
    chown -R mkuser:users /data/logs /data/backups 2>/dev/null || true
fi

# ---- 1. Mot de passe PostgreSQL auto-généré ----
if [ ! -f "$PG_PWD_FILE" ]; then
    echo ">> Premier lancement : génération du mot de passe PostgreSQL..."
    PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "$PG_PASSWORD" > "$PG_PWD_FILE"
    chmod 600 "$PG_PWD_FILE"
    chown mkuser:users "$PG_PWD_FILE"
fi

PG_PASSWORD=$(cat "$PG_PWD_FILE")

# ---- 1b. Clé JWT auto-générée si non définie ----
JWT_SECRET_FILE="$DATA_DIR/.jwt_secret"
if [ -z "$JWT_SECRET_KEY" ] && [ ! -f "$JWT_SECRET_FILE" ]; then
    echo ">> Génération automatique de la clé JWT..."
    python3 -c "import secrets; print(secrets.token_urlsafe(64))" > "$JWT_SECRET_FILE"
    chmod 600 "$JWT_SECRET_FILE"
    chown mkuser:users "$JWT_SECRET_FILE"
fi

# ---- 1c. Clé Fernet pour les settings sensibles (API keys, webhooks) ----
ENCRYPTION_KEY_FILE="$DATA_DIR/.encryption_key"
if [ -z "$MEDIAKEEPER_ENCRYPTION_KEY" ] && [ ! -f "$ENCRYPTION_KEY_FILE" ]; then
    echo ">> Génération automatique de la clé de chiffrement Fernet..."
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > "$ENCRYPTION_KEY_FILE"
    chmod 600 "$ENCRYPTION_KEY_FILE"
    chown mkuser:users "$ENCRYPTION_KEY_FILE"
fi

# ---- 2. Initialiser le cluster PG si absent ----
if [ ! -f "$PG_DATA/PG_VERSION" ]; then
    echo ">> Initialisation du cluster PostgreSQL..."
    chown -R postgres:postgres "$PG_DATA"
    su - postgres -c "$PG_BIN/initdb -D $PG_DATA --encoding=UTF8 --locale=C"

    # Configurer l'authentification
    echo "host all all 127.0.0.1/32 md5" >> "$PG_DATA/pg_hba.conf"
    echo "local all all md5" >> "$PG_DATA/pg_hba.conf"

    # Écouter uniquement en local
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '127.0.0.1'/" "$PG_DATA/postgresql.conf"
    sed -i "s/#port = 5432/port = 5432/" "$PG_DATA/postgresql.conf"

    # Démarrer temporairement pour créer user + db
    touch "$PG_LOG"
    chown postgres:postgres "$PG_LOG"
    su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA -l $PG_LOG start -w"

    su - postgres -c "$PG_BIN/psql -c \"CREATE USER mediakeeper WITH PASSWORD '$PG_PASSWORD';\""
    su - postgres -c "$PG_BIN/psql -c \"CREATE DATABASE mediakeeper_db OWNER mediakeeper;\""
    su - postgres -c "$PG_BIN/psql -c \"GRANT ALL PRIVILEGES ON DATABASE mediakeeper_db TO mediakeeper;\""

    su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA stop -w"
    echo ">> Cluster PostgreSQL initialisé."
fi

# ---- 3. Démarrer PostgreSQL ----
chown -R postgres:postgres "$PG_DATA"
# Nettoyer un éventuel PID résiduel (crash précédent)
rm -f "$PG_DATA/postmaster.pid"
# Le fichier log PG doit être accessible par l'utilisateur postgres
touch "$PG_LOG"
chown postgres:postgres "$PG_LOG"
echo ">> Démarrage de PostgreSQL..."
su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA -l $PG_LOG start -w"

# Vérifier que PG est prêt
for i in $(seq 1 30); do
    if su - postgres -c "$PG_BIN/pg_isready -h 127.0.0.1 -p 5432" > /dev/null 2>&1; then
        echo ">> PostgreSQL prêt."
        break
    fi
    sleep 1
done

# ---- 4. Variables d'environnement pour FastAPI ----
export DATABASE_URL="postgresql://mediakeeper:${PG_PASSWORD}@127.0.0.1:5432/mediakeeper_db"

# Logs dir permissions
chown -R mkuser:users /data/logs /data/backups

# ---- 4b. Appliquer les migrations Alembic (idempotent) ----
# Chaque migration Alembic est écrite en no-op si la table/colonne cible
# existe déjà (guards ``if ... not in tables``), donc relancer ``upgrade
# head`` à chaque démarrage est sans danger et garantit que toute
# nouvelle migration livrée est prise en compte au prochain rebuild.
echo ">> Application des migrations Alembic..."
su -s /bin/bash mkuser -c "cd /app/backend && alembic upgrade head" || {
    echo ">> ⚠  Échec des migrations Alembic — arrêt."
    exit 1
}

# ---- 5. Lancer Uvicorn ----
echo ">> Démarrage de Mediakeeper..."
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
    echo ">> Mode DEBUG activé (reload + logs verbose)"
    exec su -s /bin/bash mkuser -c "cd /app/backend && exec env MK_PROCESS_ROLE=combined uvicorn main:app --host 0.0.0.0 --port 8888 --reload --log-level debug"
else
    if [ "$MK_SEPARATE_BACKGROUND_WORKER" = "true" ]; then
        echo ">> Mode production : séparation API web / tâches de fond"
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
