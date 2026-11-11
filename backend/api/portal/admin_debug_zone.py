"""Admin debug: take back the trophies the UTC clock gave before the time zone was saved.

Mounted under ``/api/portal/admin/debug/zone-correction``, admin role only. Simulating
writes nothing; applying backs up first and needs the plan the simulation returned.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api._portal_admin_users_helpers import client_ip, client_ua
from api.portal.deps import require_admin
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal.zone_correction import (
    ZoneCorrectionRefused,
    apply_zone_correction,
    simulate_zone_correction,
)

router = APIRouter(prefix="/admin/debug/zone-correction", tags=["portal-admin-debug"])


class ZoneCorrectionApply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str = Field(..., min_length=1, max_length=64)
    plan: str = Field(..., min_length=1, max_length=64)


@router.get("/simulate")
async def simulate_zone_correction_route(
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await simulate_zone_correction(db)
    except ZoneCorrectionRefused as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc


@router.post("/apply")
async def apply_zone_correction_route(
    body: ZoneCorrectionApply,
    request: Request,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Read before the service ends the request's transaction, which expires these rows.
    admin_user_id = admin[0].id
    try:
        return await apply_zone_correction(
            db, timezone=body.timezone, plan=body.plan, admin_user_id=admin_user_id,
            ip=client_ip(request), user_agent=client_ua(request),
        )
    except ZoneCorrectionRefused as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc
