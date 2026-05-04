"""Constants, logger and helpers shared across sub-routers."""
import json
import logging
import os
from pathlib import Path

from fastapi import HTTPException, UploadFile

logger = logging.getLogger("mediakeeper.backup_api")

MAX_BACKUP_UPLOAD_BYTES = int(os.getenv("BACKUP_UPLOAD_MAX_BYTES", str(512 * 1024 * 1024)))
UPLOAD_CHUNK_SIZE = 1024 * 1024

# Total uncompressed size cap for a backup archive — set to 2x the upload
# cap to leave headroom for legitimately compressible payloads (notably
# pg_dump.sql) while still rejecting obvious zip-bombs. Per-entry ratio
# is enforced separately by the validator (default 100x).
MAX_BACKUP_UNCOMPRESSED_BYTES = MAX_BACKUP_UPLOAD_BYTES * 2

# Whitelist of entries a legitimate backup archive may contain. Combined
# with ``BACKUP_ARCHIVE_ALLOWED_PREFIXES`` so the rotated log files under
# ``logs/`` are accepted without enumerating each one.
BACKUP_ARCHIVE_ALLOWED_NAMES = frozenset(
    {
        "manifest.json",
        "settings.json",
        "preferences.json",
        "scheduler.json",
        "watchlist.json",
        "pg_dump.sql",
        "secrets/.encryption_key",
    }
)
BACKUP_ARCHIVE_ALLOWED_PREFIXES = ("logs/",)


def _parse_components_payload(components: str) -> dict:
    try:
        payload = json.loads(components or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="backup_components_invalid") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="backup_components_invalid")
    return payload


async def _save_upload_to_path(file: UploadFile, destination: Path) -> int:
    total = 0
    with destination.open("wb") as handle:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BACKUP_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="file_too_large",
                )
            handle.write(chunk)
    return total
