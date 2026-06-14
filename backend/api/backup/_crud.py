"""Endpoints : info, create, download, delete."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.backup import (
    DEFAULT_COMPONENTS,
    create_backup,
    delete_backup,
    get_backup_path,
    list_backups,
    resolve_backup_dir,
)
from services.path_config import is_backup_dir_locked
from services.settings import get_setting

from ._schemas import BackupRequest
from ._shared import logger

router = APIRouter()


@router.get("/info")
async def backup_info(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the backup config and the list of existing backups."""
    retention = int(await get_setting(db, "backup.retention_days") or 30)
    backup_dir = await resolve_backup_dir(db)

    return {
        "backup_dir": str(backup_dir),
        "backup_dir_locked": is_backup_dir_locked(),
        "retention_days": retention,
        "default_components": DEFAULT_COMPONENTS,
        "backups": list_backups(backup_dir),
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
        dest = await create_backup(db, components=components, label=req.label)
        return {
            "success": True,
            "filename": dest.name,
            "size_bytes": dest.stat().st_size,
        }
    except Exception as e:
        logger.error("[backup] Creation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="backup_create_failed") from e


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
    if delete_backup(filename, await resolve_backup_dir(db)):
        return {"success": True}
    raise HTTPException(status_code=404, detail="backup_not_found")
