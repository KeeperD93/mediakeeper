"""Endpoints: backup directory management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.backup import list_available_backup_dirs, resolve_backup_dir, set_backup_directory
from services.path_config import is_backup_dir_locked
from services.settings import set_setting

from ._schemas import SetDirectoryRequest
from ._shared import logger

router = APIRouter()


@router.get("/directories")
async def get_backup_directories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List the directories available for backups."""
    return list_available_backup_dirs(await resolve_backup_dir(db))


@router.post("/set-directory")
async def set_backup_dir(
    req: SetDirectoryRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Change the backup destination directory."""
    try:
        set_backup_directory(req.path)
    except ValueError as exc:
        # BACKUP_PATH pins the directory in production: surface a distinct,
        # actionable code so the UI can explain the lock instead of implying
        # the path is malformed.
        if is_backup_dir_locked():
            raise HTTPException(status_code=409, detail="backup_directory_locked") from exc
        logger.warning("[backup] set-directory rejected: %s", exc)
        raise HTTPException(status_code=400, detail="backup_directory_invalid") from exc
    await set_setting(db, "backup.directory", req.path)
    return {"success": True, "backup_dir": req.path}
