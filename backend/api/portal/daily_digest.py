"""Portal daily digest endpoints — viewer-scoped.

Exposes the once-per-day "Quoi de neuf aujourd'hui ?" payload (seven
aggregated blocks) plus a dismiss endpoint so the frontend can skip the
overlay for the rest of the calendar day.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile
from services.portal import daily_digest as dd_svc

router = APIRouter(prefix="/daily-digest", tags=["portal-daily-digest"])


@router.get("")
async def get_daily_digest(
    force: bool = Query(False, description="Bypass the 1h in-memory cache"),
    db: AsyncSession = Depends(get_db),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Return the digest payload + whether it was dismissed today.

    The frontend auto-trigger on layout mount should NOT show the overlay
    when ``dismissed`` is true or ``digest.empty`` is true. The manual
    reopen flow (avatar menu) displays it regardless of ``dismissed``.
    """
    user, _ = up
    dismissed = await dd_svc.is_dismissed_today(db, user.id)
    digest = await dd_svc.build_digest(db, user, use_cache=not force)
    return {
        "dismissed": dismissed,
        "digest": digest,
    }


@router.post("/dismiss")
async def dismiss_daily_digest(
    db: AsyncSession = Depends(get_db),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Mark today's digest as dismissed for the current user."""
    user, _ = up
    date = await dd_svc.mark_dismissed(db, user.id)
    return {"success": True, "date": date}
