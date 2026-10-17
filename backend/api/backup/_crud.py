"""Endpoints : info, create, download, delete."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.backup import (
    DEFAULT_COMPONENTS,
    apply_configured_retention,
    create_backup,
    delete_backup,
    get_backup_path,
    get_retention_days,
    list_backups,
    resolve_backup_dir,
)
from services.path_config import is_backup_dir_locked

from ._schemas import BackupRequest
from ._shared import logger

router = APIRouter()


@router.get("/info")
async def backup_info(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the backup config and the list of existing backups."""
    backup_dir = await resolve_backup_dir(db)

    return {
        "backup_dir": str(backup_dir),
        "backup_dir_locked": is_backup_dir_locked(),
        "retention_days": await get_retention_days(db),
        "default_components": DEFAULT_COMPONENTS,
        # Off the event loop: listing opens every archive to read its manifest.
        "backups": await asyncio.to_thread(list_backups, backup_dir),
    }


@router.post("/create")
async def create_backup_endpoint(
    req: BackupRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Start an immediate backup with the selected components."""
    components = {**DEFAULT_COMPONENTS, **req.components}
    try:
        result = await create_backup(db, components=components, label=req.label)
    except Exception as e:
        logger.error("[backup] Creation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="backup_create_failed") from e
    dest = result.path
    # Enforce the retention policy right away, like the scheduled backup does,
    # so manual backups don't pile up until the next automatic run. A cleanup
    # failure must not mask a successful backup — log it and still return success.
    # An incomplete backup must not push complete ones out: retention waits.
    if result.failed:
        logger.warning("[backup] retention skipped, %s is incomplete", dest.name)
    else:
        try:
            await apply_configured_retention(db)
        except Exception as e:
            logger.warning("[backup] retention pass failed after manual backup: %s", e, exc_info=True)
    return {
        "success": True,
        "filename": dest.name,
        "size_bytes": dest.stat().st_size,
        "failed_components": list(result.failed),
    }


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    path = get_backup_path(filename, await resolve_backup_dir(db))
    if not path:
        raise HTTPException(status_code=404, detail="backup_not_found")
    return FileResponse(
        path=str(path),
        media_type="application/zip",
        filename=filename,
    )


@router.delete("/{filename}")
async def delete_backup_endpoint(
    filename: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    backup_dir = await resolve_backup_dir(db)
    if await asyncio.to_thread(delete_backup, filename, backup_dir):
        return {"success": True}
    raise HTTPException(status_code=404, detail="backup_not_found")
