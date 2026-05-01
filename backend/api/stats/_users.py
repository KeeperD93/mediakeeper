"""Liste + profils user, hide/unhide, delete, merge."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.database import get_db
from models.user import User
from services.stats import (
    delete_user_stats,
    get_user_profile,
    get_users_stats,
    hide_user,
    merge_user_stats,
    unhide_user,
)

logger = logging.getLogger("mediakeeper.api.stats")
router = APIRouter()


class MergeRequest(BaseModel):
    target_user_id: str


@router.get("/users")
async def users(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=500),
    sort_by: str = Query("last_seen"),
    sort_order: str = Query("desc"),
    search: str = Query(""),
    show_hidden: bool = Query(False),
    historical_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste des users with stats de playback."""
    return await get_users_stats(db, page=page, per_page=per_page,
                                  sort_by=sort_by, sort_order=sort_order,
                                  search=search, show_hidden=show_hidden,
                                  historical_only=historical_only)


@router.get("/users/{user_id}/profile")
async def user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Detailed user profile."""
    return await get_user_profile(db, user_id=user_id)


@router.get("/user_profile")
async def user_profile_query(
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Detailed user profile (via query param for special characters)."""
    logger.debug(f"API Request: fetching profile for user_id='{user_id}'")
    try:
        return await get_user_profile(db, user_id=user_id)
    except Exception as e:
        logger.error(f"Error fetching profile for user_id='{user_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="user_profile_failed")


@router.post("/users/{user_id}/hide")
async def hide_user_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Masque un user des statistiques."""
    hidden = await hide_user(db, user_id)
    logger.info(f"User {user_id} hidden by {_.username}")
    return {"hidden_users": hidden}


@router.post("/users/{user_id}/unhide")
async def unhide_user_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Unhide a hidden user."""
    hidden = await unhide_user(db, user_id)
    logger.info(f"User {user_id} unhidden by {_.username}")
    return {"hidden_users": hidden}


@router.delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete all playback data for one user."""
    deleted = await delete_user_stats(db, user_id)
    logger.info(f"{deleted} session(s) deleted for user {user_id} by {_.username}")
    return {"deleted": deleted}


@router.post("/users/{user_id}/merge")
async def merge_user_endpoint(
    user_id: str,
    req: MergeRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Merge one user's data into another."""
    if user_id == req.target_user_id:
        raise HTTPException(status_code=400, detail="cannot_merge_self")
    merged = await merge_user_stats(db, source_user_id=user_id, target_user_id=req.target_user_id)
    logger.info(f"{merged} session(s) merged from {user_id} to {req.target_user_id} by {_.username}")
    return {"merged": merged}


@router.get("/portal-monthly-leaderboard")
async def portal_monthly_leaderboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Top portal users by XP for the current month.

    Served under ``/api/stats`` with MediaKeeper admin auth so the
    backoffice dashboard widget can render without requiring the admin
    to also hold a Portal session cookie (which was causing a 401 on
    first load). The payload is intentionally aggregate-only — no
    per-viewer ranking, no personal stats.
    """
    from services.portal.profile_stats_ranking import compute_leaderboard_only
    try:
        return {"leaderboard": await compute_leaderboard_only(db)}
    except Exception as e:
        logger.debug(f"[PORTAL-LEADERBOARD] error: {e}")
        return {"leaderboard": []}
