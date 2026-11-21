"""Admin debug: recalculate the watch XP of every player with the current rule.

Mounted under ``/api/portal/admin/debug/watch-xp``, admin role only. Simulating writes
nothing; applying backs up first and needs the moment and the plan the simulation returned.
"""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api._portal_admin_users_helpers import client_ip, client_ua
from api.portal.deps import require_admin
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal.watch_xp_recalc import (
    WatchXpRecalcRefused,
    apply_watch_xp_recalc,
    simulate_watch_xp_recalc,
)

router = APIRouter(prefix="/admin/debug/watch-xp", tags=["portal-admin-debug"])


class WatchXpApply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: datetime
    plan: str = Field(..., min_length=1, max_length=64)


@router.get("/simulate")
async def simulate_watch_xp_route(
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await simulate_watch_xp_recalc(db)


@router.post("/apply")
async def apply_watch_xp_route(
    body: WatchXpApply,
    request: Request,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Read before the service ends the request's transaction, which expires these rows.
    admin_user_id = admin[0].id
    as_of = body.as_of if body.as_of.tzinfo else body.as_of.replace(tzinfo=UTC)
    try:
        return await apply_watch_xp_recalc(
            db, as_of=as_of, plan=body.plan, admin_user_id=admin_user_id,
            ip=client_ip(request), user_agent=client_ua(request),
        )
    except WatchXpRecalcRefused as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc
