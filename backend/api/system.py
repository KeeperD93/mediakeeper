"""Admin system API — new-version check shown in the sidebar footer."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.changelog import APP_VERSION
from core.database import get_db
from models.user import User
from services.update_check import get_update_status, set_update_check_enabled

router = APIRouter(prefix="/api/system", tags=["system"])


class UpdateCheckToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


@router.get("/update-check")
async def get_update_check(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Current vs newest published version (GitHub lookup cached six hours)."""
    return await get_update_status(db, APP_VERSION)


@router.put("/update-check")
async def put_update_check(
    payload: UpdateCheckToggle,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Turn the check on or off; returns the refreshed status."""
    await set_update_check_enabled(db, payload.enabled)
    return await get_update_status(db, APP_VERSION)
