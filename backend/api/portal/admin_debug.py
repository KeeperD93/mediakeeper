"""Admin debug endpoints — XP / level / achievement edits.

Mounted under ``/api/portal/admin/debug``. Every route requires the
admin role (via ``require_admin``); regular viewers cannot reach it.
Kept out of ``admin.py`` to honour the 300-line file-size cap.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import require_admin
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal import admin_debug
from services.portal.achievement_defs import ACHIEVEMENT_DEFS


router = APIRouter(prefix="/admin/debug", tags=["portal-admin-debug"])


class GrantXpRequest(BaseModel):
    user_id: int
    amount: int = Field(..., ge=-100000, le=100000)
    note: str | None = Field(None, max_length=120)


class SetLevelRequest(BaseModel):
    user_id: int
    level: int = Field(..., ge=0, le=50)


class AchievementToggleRequest(BaseModel):
    user_id: int
    achievement_id: str = Field(..., min_length=1, max_length=120)


class ResetAchievementForAllRequest(BaseModel):
    achievement_id: str = Field(..., min_length=1, max_length=120)


@router.get("/users")
async def debug_list_users(
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Light user list for the debug picker — username, level, xp, role.
    Returns admins too on purpose: admins can be the target of debug
    operations (e.g. testing trophies on the admin account)."""
    rows = (await db.execute(
        select(User.id, User.username, UserProfile.display_name,
               UserProfile.level, UserProfile.xp, UserProfile.role,
               UserProfile.account_active)
        .select_from(User)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(User.is_active.is_(True))
        .order_by(UserProfile.role.asc(), User.username.asc())
    )).all()
    return {
        "items": [
            {
                "user_id": r[0],
                "username": r[1],
                "display_name": r[2] or r[1],
                "level": r[3] or 0,
                "xp": r[4] or 0,
                "role": r[5] or "viewer",
                "account_active": bool(r[6]),
            }
            for r in rows
        ]
    }


@router.get("/achievements")
async def debug_list_achievements(
    _: tuple[User, UserProfile] = Depends(require_admin),
):
    """Flat catalogue of every achievement so the picker can list them
    grouped by category. Reads the in-memory defs (not the DB) so this
    works even before ``check_all_achievements`` has stamped progress."""
    return {
        "items": [
            {
                "id": d["id"],
                "name_key": d["name_key"],
                "description_key": d.get("description_key"),
                "category": d.get("category", "misc"),
                "tier": d.get("tier", 1),
                "secret": bool(d.get("secret")),
                "threshold": d.get("threshold", 1),
                "xp_reward": d.get("xp_reward", 0),
            }
            for d in ACHIEVEMENT_DEFS
        ]
    }


@router.post("/grant-xp")
async def debug_grant_xp(
    body: GrantXpRequest,
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await admin_debug.admin_grant_xp(
        db, body.user_id, body.amount, note=body.note,
    )
    if res is None:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return res


@router.post("/set-level")
async def debug_set_level(
    body: SetLevelRequest,
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await admin_debug.admin_set_level(db, body.user_id, body.level)
    if res is None:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return res


@router.post("/unlock-achievement")
async def debug_unlock_achievement(
    body: AchievementToggleRequest,
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await admin_debug.admin_unlock_achievement(
        db, body.user_id, body.achievement_id,
    )
    if res is None:
        raise HTTPException(status_code=404, detail="achievement_not_found")
    return res


@router.post("/lock-achievement")
async def debug_lock_achievement(
    body: AchievementToggleRequest,
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await admin_debug.admin_lock_achievement(
        db, body.user_id, body.achievement_id,
    )
    if res is None:
        raise HTTPException(status_code=404, detail="achievement_not_found")
    return res


@router.post("/reset-achievement-for-all")
async def debug_reset_achievement_for_all(
    body: ResetAchievementForAllRequest,
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Wipe a specific achievement and its XP from every user.

    Pair with ``recheck-all-achievements`` to scrub a trophy that was
    unlocked through a counter bug — only users who still qualify will
    re-earn it on the next pass.
    """
    res = await admin_debug.admin_reset_achievement_for_all(db, body.achievement_id)
    if res is None:
        raise HTTPException(status_code=404, detail="achievement_not_found")
    return res


@router.post("/recheck-all-achievements")
async def debug_recheck_all_achievements(
    _: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Run ``check_all_achievements`` for every active profile.

    Used to backfill trophies after a bug that prevented the post-session
    pipeline from running (the collector usually triggers the check, but
    only for users who played since the bug was fixed). The check is
    idempotent — already-unlocked achievements are skipped via the
    ``unlocked_ids`` guard, and grant_xp dedup blocks XP double-counting.
    """
    from services.portal.achievements import safe_check_all_achievements

    profiles = (await db.execute(
        select(UserProfile, User.username)
        .join(User, User.id == UserProfile.user_id)
        .where(UserProfile.account_active.is_(True))
    )).all()

    summary = []
    total_unlocks = 0
    for profile, username in profiles:
        unlocks = await safe_check_all_achievements(
            db, profile.user_id, username, source="admin_recheck", silent=True,
        )
        if unlocks:
            total_unlocks += len(unlocks)
            summary.append({
                "user_id": profile.user_id,
                "username": username,
                "newly_unlocked": len(unlocks),
                "achievement_ids": [u["achievement_id"] for u in unlocks],
            })
    return {
        "users_processed": len(profiles),
        "users_with_new_unlocks": sum(1 for s in summary if s.get("newly_unlocked")),
        "total_new_unlocks": total_unlocks,
        "details": summary,
    }
