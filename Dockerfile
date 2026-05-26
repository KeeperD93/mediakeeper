# ============================================
# STAGE 1: Build the Vue 3 frontend
# ============================================
FROM node:24-alpine AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ============================================
# STAGE 2: Python application + built frontend
# ============================================
FROM python:3.14-slim

# ============================================
# System dependencies: PostgreSQL 16 + curl (healthcheck)
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
# ffmpeg (separate layer for independent caching)
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ============================================
# Application user
# ============================================
RUN adduser --system --ingroup users --shell /bin/bash --home /home/mkuser mkuser

# ============================================
# Python application
# ============================================
WORKDIR /app

COPY backend/requirements.txt .
# gcc + python3-dev are installed transiently so that pip can compile
# C extensions for the linux/arm64 multi-arch build (psutil, cryptography,
# etc. ship aarch64 wheels for amd64 but not always for the slim image's
# manylinux variant on arm64, forcing a source build). libffi-dev and
# libssl-dev are added defensively for cryptography. All build tools are
# purged in the same layer so they do not bloat the runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc python3-dev libffi-dev libssl-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc python3-dev libffi-dev libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY backend/ ./backend/

# Vue 3 frontend (build output from stage 1)
COPY --from=frontend-build /build/dist/ ./frontend-dist/

# ============================================
# Persistent directories
# ============================================
# /data/avatars holds custom uploads served by the Portal — without
# the pre-created subdir the FastAPI handler raises PermissionError
# on the first upload because the volume root is owned by an
# unrelated UID when the host mounts an empty volume. Pre-creating +
# chowning here, plus a defensive re-chown in entrypoint.sh, covers
# both fresh installs and existing volumes that pre-date this fix.
RUN mkdir -p /data/pg /data/logs /data/backups /data/avatars \
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
