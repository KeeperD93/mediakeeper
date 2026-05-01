"""Constants, logger and helpers shared across sub-routers."""
import json
import logging
import os
from pathlib import Path

from fastapi import HTTPException, UploadFile

logger = logging.getLogger("mediakeeper.backup_api")

MAX_BACKUP_UPLOAD_BYTES = int(os.getenv("BACKUP_UPLOAD_MAX_BYTES", str(512 * 1024 * 1024)))
UPLOAD_CHUNK_SIZE = 1024 * 1024


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
