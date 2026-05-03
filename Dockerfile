# ============================================
# STAGE 1 : Build frontend Vue 3
# ============================================
FROM node:20-alpine AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ============================================
# STAGE 2 : Application Python + frontend built
# ============================================
FROM python:3.12-slim

# ============================================
# Dépendances système : PostgreSQL 16 + curl (healthcheck)
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg2 curl ca-certificates lsb-release tzdata \
    && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg \
    && apt-get update && apt-get install -y --no-install-recommends \
        postgresql-16 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ============================================
# ffmpeg (layer séparé pour cache indépendant)
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ============================================
# Utilisateur applicatif
# ============================================
RUN adduser --system --ingroup users --shell /bin/bash --home /home/mkuser mkuser

# ============================================
# Application Python
# ============================================
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

# Frontend Vue 3 (build output depuis stage 1)
COPY --from=frontend-build /build/dist/ ./frontend-dist/

# ============================================
# Répertoires persistants
# ============================================
RUN mkdir -p /data/pg /data/logs /data/backups \
    && chown -R mkuser:users /data \
    && chown -R postgres:postgres /data/pg


# ============================================
# Entrypoint
# ============================================
COPY entrypoint.sh /app/entrypoint.sh
# Strip CRLF if a Windows checkout slipped through gitattributes.
# Self-healing — the image always has LF regardless of source line endings.
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f "http://localhost:8888/api/health" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
