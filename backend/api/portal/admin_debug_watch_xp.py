"""Admin debug: recalculate the watch XP of every player with the current rule.

Mounted under ``/api/portal/admin/debug/watch-xp``, admin role only. Simulating writes
nothing.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import require_admin
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal.watch_xp_recalc import simulate_watch_xp_recalc

router = APIRouter(prefix="/admin/debug/watch-xp", tags=["portal-admin-debug"])


@router.get("/simulate")
async def simulate_watch_xp_route(
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await simulate_watch_xp_recalc(db)
