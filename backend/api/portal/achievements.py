"""Portal achievement and leaderboard endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import limiter, portal_user_or_ip_key
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile, get_request_lang
from services.portal import achievements as ach_svc
from services.portal.profile_stats_ranking import (
    LEADERBOARD_FULL_DEFAULT,
    compute_leaderboard_only,
)

router = APIRouter(prefix="/achievements", tags=["portal-achievements"])


@router.get("")
async def list_achievements(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get all achievements with current user's progress + rarity."""
    user, _ = up
    return await ach_svc.get_achievements_for_profile(db, user.id)


@router.get("/me")
async def my_achievements(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's achievement progress (profile page format)."""
    user, _ = up
    return await ach_svc.get_achievements_for_profile(db, user.id)


@router.get("/user/{user_id}")
async def user_achievements(
    user_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get another user's achievements (only unlocked shown).

    Visibility mirrors the public profile rules in
    ``profile_settings.public_profile_by_user``: 404 when the target
    profile is missing, deactivated, or admin (unless the caller is
    looking at themselves), and 403 when the target keeps their
    profile private. Without this gate an attacker could enumerate the
    admin account's trophies even when ``role=admin`` profiles are
    hidden everywhere else.
    """
    me, _ = up
    target = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )).scalar_one_or_none()
    if not target or not target.account_active:
        raise HTTPException(status_code=404, detail="profile_not_found")
    is_self = me.id == user_id
    if target.role == "admin" and not is_self:
        raise HTTPException(status_code=404, detail="profile_not_found")
    if not is_self and not target.is_public:
        # Same fail-closed shape as the public profile endpoint: 404
        # for any account the caller cannot read, regardless of the
        # underlying reason.
        raise HTTPException(status_code=404, detail="profile_not_found")

    data = await ach_svc.get_achievements_for_profile(db, user_id)
    data["items"] = [a for a in data["items"] if a["status"] == "unlocked"]
    return data


class PinRequest(BaseModel):
    achievement_id: str


@router.post("/pin")
async def pin_badge(
    body: PinRequest,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Pin an unlocked achievement to profile (max 5)."""
    user, _ = up
    ok = await ach_svc.pin_badge(db, user.id, body.achievement_id)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(400, "Cannot pin: not unlocked or max 5 reached")
    return {"ok": True}


@router.post("/unpin")
async def unpin_badge(
    body: PinRequest,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Unpin a badge from profile."""
    user, _ = up
    await ach_svc.unpin_badge(db, user.id, body.achievement_id)
    return {"ok": True}


@router.post("/check")
async def check_achievements(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Force-check all achievements for current user. Returns newly unlocked."""
    user, profile = up
    unlocks = await ach_svc.safe_check_all_achievements(
        db, user.id, user.username, source="manual_check", silent=False,
    )
    return {"unlocked": unlocks}


@router.get("/leaderboard")
async def leaderboard(
    limit: int = Query(20, ge=1, le=100),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    """Top users by XP with achievement count."""
    return {"items": await ach_svc.get_leaderboard(db, limit, lang=lang)}


@router.get("/leaderboard/monthly")
@limiter.limit("60/minute", key_func=portal_user_or_ip_key)
async def monthly_leaderboard(
    request: Request,
    limit: int = Query(LEADERBOARD_FULL_DEFAULT, ge=1, le=LEADERBOARD_FULL_DEFAULT),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    """Top players by *monthly* XP — feeds the dedicated /portal/leaderboard page.

    Shares its trust boundary with the profile mini-leaderboard: any
    authenticated portal user can view the full ranking, the excluded
    users (admin, soft-deleted, deactivated) are filtered out by
    :func:`compute_leaderboard_only` itself, and the payload schema
    matches the embedded ``compute_ranking().leaderboard`` entries
    (rank, user_id, display_name, avatar_url, level, tier, title_key,
    month_xp, selected_title, title_tier, is_current_user, movement).
    """
    return {"items": await compute_leaderboard_only(db, limit=limit, lang=lang)}
