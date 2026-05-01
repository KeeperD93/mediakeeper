"""Endpoints: backup directory management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.backup import list_available_backup_dirs, set_backup_directory
from services.settings import set_setting

from ._schemas import SetDirectoryRequest

router = APIRouter()


@router.get("/directories")
async def get_backup_directories(
    _: User = Depends(get_current_user),
):
    """List the directories available for backups."""
    return list_available_backup_dirs()


@router.post("/set-directory")
async def set_backup_dir(
    req: SetDirectoryRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Change the backup destination directory."""
    try:
        set_backup_directory(req.path)
        await set_setting(db, "backup.directory", req.path)
        return {"success": True, "backup_dir": req.path}
    except ValueError:
        raise HTTPException(status_code=400, detail="backup_directory_invalid")
