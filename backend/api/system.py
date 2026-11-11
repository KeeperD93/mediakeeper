"""Admin system API: new-version check and time zone of the instance."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api._portal_admin_users_helpers import client_ip, client_ua
from api.auth import get_current_user
from api.changelog import APP_VERSION
from core.database import get_db
from models.user import User
from services.instance_time import INSTANCE_TIMEZONE_KEY, get_timezone_status, is_known_zone
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import ACTION_SYSTEM_TIMEZONE_CHANGED
from services.settings import get_setting, set_setting
from services.update_check import get_update_status, set_update_check_enabled

router = APIRouter(prefix="/api/system", tags=["system"])


class UpdateCheckToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class TimezoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str = Field(max_length=64)


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


@router.get("/timezone")
async def get_timezone(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Zone saved, zone in use and the zones to choose from."""
    return await get_timezone_status(db)


@router.put("/timezone")
async def put_timezone(
    payload: TimezoneUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    """Save the zone, traced because trophies gained through it are not taken back."""
    if not await is_known_zone(payload.timezone):
        raise HTTPException(status_code=422, detail="invalid_timezone")
    previous = await get_setting(db, INSTANCE_TIMEZONE_KEY)
    if payload.timezone != previous:
        await set_setting(db, INSTANCE_TIMEZONE_KEY, payload.timezone, commit=False)
        await record_audit(
            db,
            admin_user_id=admin.id,
            target_user_id=None,
            action=ACTION_SYSTEM_TIMEZONE_CHANGED,
            payload={"from": previous or None, "to": payload.timezone},
            ip=client_ip(request),
            user_agent=client_ua(request),
            commit=False,
        )
        await db.commit()
    return await get_timezone_status(db)
