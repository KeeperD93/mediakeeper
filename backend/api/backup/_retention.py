"""Endpoints: retention (config + immediate application)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.backup import RETENTION_DAYS_KEY, apply_configured_retention
from services.settings import set_setting

from ._schemas import RetentionRequest

router = APIRouter()


@router.post("/retention")
async def set_retention(
    req: RetentionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await set_setting(db, RETENTION_DAYS_KEY, str(req.days))
    return {"success": True, "days": req.days}


@router.post("/apply-retention")
async def apply_retention_now(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    removed = await apply_configured_retention(db)
    return {"success": True, "removed": removed}
