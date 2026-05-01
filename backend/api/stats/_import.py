"""Import / purge of a Jellystats backup."""
import json
import logging

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.stats import import_jellystats_backup, purge_jellystats_import

logger = logging.getLogger("mediakeeper.api.stats")
router = APIRouter()

_MAX_IMPORT_SIZE = 200 * 1024 * 1024  # 200 MB
_IMPORT_CHUNK_SIZE = 1024 * 1024


async def _read_limited_json_upload(file: UploadFile) -> bytes:
    content = bytearray()
    while True:
        chunk = await file.read(_IMPORT_CHUNK_SIZE)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > _MAX_IMPORT_SIZE:
            size_mb = len(content) // (1024 * 1024)
            raise ValueError(f"File too large ({size_mb} MB). Maximum: 200 MB")
    return bytes(content)


@router.post("/import/jellystats")
async def import_jellystats(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Import a Jellystats backup (JSON).
    Imports jf_playback_activity -> playback_sessions
    and jf_libraries -> library_cache.
    """
    if not (file.filename or "").lower().endswith(".json"):
        return {"error": "File must be in JSON format"}

    try:
        content = await _read_limited_json_upload(file)
        data = json.loads(content)
    except Exception as e:
        return {"error": f"Unable to read JSON: {e}"}

    try:
        return await import_jellystats_backup(db, data)
    except Exception as e:
        logger.error(f"Error import Jellystats: {e}", exc_info=True)
        return {"error": f"Error during import: {str(e)[:200]}"}


@router.post("/import/jellystats/purge")
async def purge_jellystats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Remove only the data imported from Jellystats."""
    return await purge_jellystats_import(db)
