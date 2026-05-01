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
    get_current_backup_dir,
    list_backups,
)
from services.settings import get_setting

from ._schemas import BackupRequest
from ._shared import logger

router = APIRouter()


@router.get("/info")
async def backup_info(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return la config backup + liste des backups existants."""
    retention = int(await get_setting(db, "backup.retention_days") or 30)
    backup_path_env = str(get_current_backup_dir())

    return {
        "backup_dir": backup_path_env,
        "retention_days": retention,
        "default_components": DEFAULT_COMPONENTS,
        "backups": list_backups(),
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
        logger.error(f"[backup] Creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="backup_create_failed")


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    _: User = Depends(get_current_user),
):
    path = get_backup_path(filename)
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
    _: User = Depends(get_current_user),
):
    if delete_backup(filename):
        return {"success": True}
    raise HTTPException(status_code=404, detail="backup_not_found")
