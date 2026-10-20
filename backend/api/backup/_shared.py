"""Constants, logger and helpers shared across sub-routers."""
import asyncio
import logging
import os
from pathlib import Path

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from services.backup import COMPONENTS_ADAPTER

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
        return COMPONENTS_ADAPTER.validate_json(components or "{}")
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="backup_components_invalid") from exc


async def _save_upload_to_path(file: UploadFile, destination: Path) -> int:
    """Copy the upload to ``destination``, the disk writes off the event loop."""
    total = 0
    handle = await asyncio.to_thread(destination.open, "wb")
    try:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            total += len(chunk)
            if total > MAX_BACKUP_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="file_too_large")
            await asyncio.to_thread(handle.write, chunk)
    finally:
        await asyncio.to_thread(handle.close)
    return total
