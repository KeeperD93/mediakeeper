"""Endpoints: retention (config + immediate application)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.backup import apply_retention, apply_retention_by_count, resolve_backup_dir
from services.settings import get_setting, set_setting

from ._schemas import RetentionRequest

router = APIRouter()


@router.post("/retention")
async def set_retention(
    req: RetentionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await set_setting(db, "backup.retention_days", str(req.days))
    return {"success": True, "days": req.days}


@router.post("/apply-retention")
async def apply_retention_now(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    retention = int(await get_setting(db, "backup.retention_days") or 30)
    backup_dir = await resolve_backup_dir(db)
    if retention < 0:
        removed = apply_retention_by_count(abs(retention), backup_dir)
    else:
        removed = apply_retention(retention, backup_dir)
    return {"success": True, "removed": removed}
