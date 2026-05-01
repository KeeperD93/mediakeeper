"""Premium settings endpoints — username availability check, custom avatar
upload / delete, file serving, and rich public profile lookup with the
achievement ratio panel needed by the public profile page.

These endpoints are split out of ``profiles.py`` to keep that file under
the 300-line file-size cap. The router is mounted under the same
``/profiles`` prefix so URLs stay consistent on the client.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.user import User
from api.portal.deps import get_current_profile
from services.portal.achievement_defs import ACHIEVEMENT_DEFS
from services.portal.avatars import (
    avatar_path_for, avatar_public_url, delete_avatar, save_avatar,
)
from services.portal.profile_stats_ranking import compute_ranking
from services.portal.profiles import (
    DISPLAY_NAME_LOCK_DAYS, _serialize_public, display_name_locked_until,
    is_display_name_locked, is_display_name_taken, is_reserved_display_name,
    sanitize, suggest_display_names,
)


router = APIRouter(prefix="/profiles", tags=["portal-profile-settings"])

avatar_router = APIRouter(prefix="/avatars", tags=["portal-avatars"])

PUBLIC_TOTAL_ACHIEVEMENTS = sum(
    1 for d in ACHIEVEMENT_DEFS if not d.get("hidden_from_total")
)


# ─────────────────────────────────────────────────────────────────────────
# Username availability + lock state
# ─────────────────────────────────────────────────────────────────────────


@router.get("/me/check-username")
async def check_username(
    name: str = Query(..., min_length=1, max_length=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Live validation for the username field.

    Returns ``{available, reason, locked_until}``. ``available`` is true when
    the user can take this name right now: the candidate is well-formed,
    not taken by someone else (case-insensitive), and the user is either
    setting it for the first time or out of the 6-month cooldown.
    """
    user, profile = up
    cleaned = sanitize(name, max_len=50)
    if not cleaned:
        return {
            "available": False, "reason": "invalid",
            "locked_until": None, "suggestions": [],
        }

    locked_until = display_name_locked_until(profile)
    locked = is_display_name_locked(profile)
    same_as_current = cleaned.lower() == (profile.display_name or "").lower()
    locked_iso = locked_until.isoformat() if locked_until else None

    if same_as_current:
        return {
            "available": True, "reason": "current",
            "locked_until": locked_iso, "suggestions": [],
        }

    if locked:
        return {
            "available": False, "reason": "locked",
            "locked_until": locked_iso, "suggestions": [],
        }

    if profile.role != "admin" and is_reserved_display_name(cleaned):
        return {
            "available": False, "reason": "reserved",
            "locked_until": locked_iso, "suggestions": [],
        }

    taken = await is_display_name_taken(db, cleaned, exclude_user_id=user.id)
    suggestions: list[str] = []
    if taken:
        suggestions = await suggest_display_names(
            db, cleaned, exclude_user_id=user.id, limit=5,
        )
    return {
        "available": not taken,
        "reason": "taken" if taken else "free",
        "locked_until": locked_iso,
        "suggestions": suggestions,
    }


@router.get("/me/username-state")
async def username_state(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Surface the cooldown info without round-tripping a candidate name."""
    _, profile = up
    locked_until = display_name_locked_until(profile)
    return {
        "must_set": bool(profile.display_name_must_set),
        "locked": is_display_name_locked(profile),
        "locked_until": locked_until.isoformat() if locked_until else None,
        "lock_days": DISPLAY_NAME_LOCK_DAYS,
        "current": profile.display_name,
    }


# ─────────────────────────────────────────────────────────────────────────
# Custom avatar upload / delete / serve
# ─────────────────────────────────────────────────────────────────────────


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Replace the user's custom avatar; previous file is deleted."""
    user, profile = up
    previous = profile.avatar_custom_path
    stored = await save_avatar(user.id, file)
    delete_avatar(previous)
    profile.avatar_custom_path = stored
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {
        "avatar_custom_path": stored,
        "avatar_url": avatar_public_url(stored),
    }


@router.delete("/me/avatar")
async def delete_my_avatar(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Drop the custom avatar; the Emby-proxied avatar takes back over."""
    _, profile = up
    delete_avatar(profile.avatar_custom_path)
    profile.avatar_custom_path = None
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {
        "avatar_custom_path": None,
        "avatar_url": profile.avatar_url,
    }


@avatar_router.get("/{filename}")
async def serve_avatar(
    filename: str,
    _: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Stream a stored avatar back to authenticated portal users.

    Auth is required because portal accounts can be private and we don't
    want avatars indexable through guessable URLs. The endpoint enforces
    path containment via ``avatar_path_for``.
    """
    target = avatar_path_for(filename)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="avatar_not_found")
    return FileResponse(
        target,
        media_type=_guess_mime(filename),
        headers={"Cache-Control": "private, max-age=86400"},
    )


def _guess_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp", "gif": "image/gif",
    }.get(ext, "application/octet-stream")


# ─────────────────────────────────────────────────────────────────────────
# Rich public profile (used by /portal/u/:id)
# ─────────────────────────────────────────────────────────────────────────


@router.get("/by-user-id/{user_id}/public")
async def public_profile_by_user(
    user_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Public profile keyed by ``user_id`` (matches the URL the leaderboard
    builds). Augments the bare public payload with the achievement ratio
    and the unlocked achievement IDs so the client can render the trophy
    grid without leaking unlock methods or progress."""
    me, _ = up

    row = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )).scalar_one_or_none()

    if not row or not row.account_active:
        raise HTTPException(status_code=404, detail="profile_not_found")

    is_self = me.id == user_id

    # Admin profiles are not consultable by others (404). Self-lookup is
    # allowed so an admin can hit "View my public profile" and preview
    # the page without triggering a dead end — the response simply
    # carries an ``admin_preview`` flag the UI can use to show "your
    # profile is not visible to others".
    if row.role == "admin" and not is_self:
        raise HTTPException(status_code=404, detail="profile_not_found")

    if not is_self and not row.is_public:
        raise HTTPException(status_code=403, detail="profile_private")

    base = _serialize_public(row)

    unlocked_ids = (await db.execute(
        select(UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .where(UserAchievement.unlocked.is_(True))
    )).scalars().all()
    unlocked_count = len(unlocked_ids)

    # Mirror /portal/me: rank position is the monthly XP ladder, not
    # all-time XP, so a user opening their public profile sees the
    # same "#3 this month" they read on the dashboard sidebar.
    target_user = (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    monthly = await compute_ranking(db, target_user) if target_user else {}
    rank_position = monthly.get("position") or 0
    rank_total = monthly.get("total") or 0
    rank_percentile = monthly.get("percentile") or 0
    rank_movement = monthly.get("movement") or 0

    member_since_months = 0
    if row.created_at:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - created_at
        member_since_months = max(1, delta.days // 30)

    return {
        **base,
        "is_self": is_self,
        "admin_preview": row.role == "admin" and is_self,
        "achievements": {
            "unlocked": unlocked_count,
            "total": PUBLIC_TOTAL_ACHIEVEMENTS,
            "unlocked_ids": list(unlocked_ids),
        },
        "ranking": {
            "position": rank_position,
            "total_public": rank_total,
            "percentile": rank_percentile,
            "movement": rank_movement,
        },
        "member_since_months": member_since_months,
    }
