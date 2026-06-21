"""Portal profile endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile, get_request_lang
from services.portal._display_name import resolve_display_name
from services.portal._rank_tiers import tier_for_level
from services.portal.achievement_defs import TITLE_REWARDS
from services.portal.achievement_defs_meta import META_TARGET_CATEGORY
from services.portal.avatars import resolve_avatar_url
from services.portal.profiles import (
    update_profile, serialize_profile_with_effective_lang,
)

router = APIRouter(prefix="/profiles", tags=["portal-profiles"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ``avatar_url`` is intentionally omitted: a custom MediaKeeper avatar is
    # uploaded via POST /me/avatar (see api/portal/profile_settings.py),
    # while the Emby-proxied URL is owned by the auth flow.
    display_name: Optional[str] = Field(None, min_length=1, max_length=50)
    bio: Optional[str] = Field(None, max_length=500)
    favorite_genres: Optional[list[int]] = None
    selected_badges: Optional[list[str]] = Field(None, max_length=5)
    selected_title: Optional[str] = Field(None, max_length=100)
    avatar_effect: Optional[str] = Field(None, max_length=50)
    is_public: Optional[bool] = None
    language: Optional[str] = Field(None, min_length=2, max_length=10)
    hide_adult: Optional[bool] = None


async def _user_unlocked_titles(db: AsyncSession, user_id: int) -> set[str]:
    """Return the set of title_keys the user has earned via unlocked achievements."""
    rows = (await db.execute(
        select(UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .where(UserAchievement.unlocked.is_(True))
    )).scalars().all()
    return {TITLE_REWARDS[a] for a in rows if a in TITLE_REWARDS}


async def _user_unlocked_avatar_effects(db: AsyncSession, user_id: int) -> set[str]:
    """Return the set of avatar_effect values the user has earned via unlocked
    meta-achievements. Each Master grants one avatar cosmetic keyed by its
    target_category (e.g. 'watching', 'dedication'...)."""
    rows = (await db.execute(
        select(UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .where(UserAchievement.unlocked.is_(True))
    )).scalars().all()
    return {META_TARGET_CATEGORY[a] for a in rows if a in META_TARGET_CATEGORY}


async def _user_unlocked_achievement_ids(db: AsyncSession, user_id: int) -> set[str]:
    rows = (await db.execute(
        select(UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .where(UserAchievement.unlocked.is_(True))
    )).scalars().all()
    return set(rows)


async def _stale_decoration_updates(
    db: AsyncSession, profile: UserProfile, user_id: int,
) -> dict:
    """Equipped cosmetics on ``profile`` that no longer reference an unlocked
    achievement, as a ``{column: cleaned_value}`` map (empty when nothing is
    stale). Pure read — the caller decides whether to persist (the owner's own
    profile) or just hide them for display (a third party's public view)."""
    updates: dict = {}
    if profile.selected_title and (
        profile.selected_title not in await _user_unlocked_titles(db, user_id)
    ):
        updates["selected_title"] = None
    if profile.avatar_effect and (
        profile.avatar_effect not in await _user_unlocked_avatar_effects(db, user_id)
    ):
        updates["avatar_effect"] = None
    if profile.selected_badges:
        unlocked = await _user_unlocked_achievement_ids(db, user_id)
        kept = [b for b in profile.selected_badges if b in unlocked]
        if len(kept) != len(profile.selected_badges):
            updates["selected_badges"] = kept or None
    return updates


async def _prune_stale_decorations(
    db: AsyncSession, profile: UserProfile, user_id: int,
) -> UserProfile:
    """Clear equipped cosmetics that no longer reference unlocked achievements
    and persist — the dropdowns filter locked items, so without this the user
    keeps cosmetics they cannot re-select. Owner's own profile only (it writes)."""
    updates = await _stale_decoration_updates(db, profile, user_id)
    if updates:
        for field, value in updates.items():
            setattr(profile, field, value)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.get("/me")
async def get_my_profile(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    profile = await _prune_stale_decorations(db, profile, user.id)
    return await serialize_profile_with_effective_lang(db, profile, user=user)


@router.get("/me/titles")
async def list_my_titles(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """List title keys unlocked by the current user, plus the currently equipped
    one and the full catalogue (title → source achievement) so the UI can show
    a "how to unlock" panel."""
    from services.portal.achievement_defs import TITLE_REWARDS, ACHIEVEMENT_DEFS
    user, profile = up
    unlocked = await _user_unlocked_titles(db, user.id)
    catalogue = []
    for ach_id, title_key in TITLE_REWARDS.items():
        ach_def = next((d for d in ACHIEVEMENT_DEFS if d["id"] == ach_id), None)
        if not ach_def:
            continue
        catalogue.append({
            "title_key": title_key,
            "achievement_id": ach_id,
            "achievement_name_key": ach_def["name_key"],
            "achievement_description_key": ach_def["description_key"],
            "tier": ach_def.get("tier", 1),
            "secret": ach_def.get("secret", False),
            "unlocked": title_key in unlocked,
        })
    return {
        "titles": sorted(unlocked),
        "selected_title": profile.selected_title,
        "catalogue": catalogue,
    }


@router.get("/me/avatar-effects")
async def list_my_avatar_effects(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """List avatar effects unlocked by the current user (one per Master
    mastered) plus the currently equipped one. The UI uses this to populate
    the "avatar cosmetic" dropdown under titles in the profile edit modal."""
    user, profile = up
    unlocked = await _user_unlocked_avatar_effects(db, user.id)
    return {
        "effects": sorted(unlocked),
        "avatar_effect": profile.avatar_effect,
    }


@router.put("/me")
async def update_my_profile(
    data: ProfileUpdate,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, profile = up
    if profile.forced_public and data.is_public is False:
        raise HTTPException(status_code=403, detail="profile_visibility_locked")
    payload = data.model_dump(exclude_unset=True)
    if "selected_title" in payload and payload["selected_title"] is not None:
        unlocked = await _user_unlocked_titles(db, user.id)
        if payload["selected_title"] not in unlocked:
            raise HTTPException(status_code=403, detail="title_not_unlocked")
    if "avatar_effect" in payload and payload["avatar_effect"]:
        unlocked_fx = await _user_unlocked_avatar_effects(db, user.id)
        if payload["avatar_effect"] not in unlocked_fx:
            raise HTTPException(status_code=403, detail="avatar_effect_not_unlocked")
    if "selected_badges" in payload and payload["selected_badges"]:
        unlocked_badges = await _user_unlocked_achievement_ids(db, user.id)
        if not set(payload["selected_badges"]).issubset(unlocked_badges):
            raise HTTPException(status_code=403, detail="badge_not_unlocked")
    updated = await update_profile(db, profile, payload)
    return await serialize_profile_with_effective_lang(db, updated, user=user)


@router.get("/search/users")
async def search_users(
    q: str = Query("", max_length=100),
    limit: int = Query(20, ge=1, le=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    """
    Lightweight user picker used by the event creation modal. Returns
    every active user matching `q` against username/display_name. We
    exclude the requesting user themselves so they can't invite their
    own account.

    The raw Emby ``User.username`` is used internally for matching but
    is never returned to the caller — accounts that haven't picked a
    portal pseudo render as the localized anonymous alias instead.
    """
    from sqlalchemy import select, or_
    me, _ = up
    needle = (q or "").strip().lower()
    # Inner-join on UserProfile so soft-deleted accounts can never leak
    # via a NULL-profile drift. The picker must mirror the visibility
    # rules of the public profile endpoint and the leaderboard.
    stmt = (
        select(
            User.id,
            User.username,
            UserProfile.display_name,
            UserProfile.display_name_must_set,
            UserProfile.avatar_url,
            UserProfile.avatar_custom_path,
            UserProfile.level,
        )
        .select_from(User)
        .join(UserProfile, UserProfile.user_id == User.id)
        .where(User.id != me.id)
        .where(User.is_active.is_(True))
        .where(UserProfile.account_active.is_(True))
        .where(UserProfile.deleted_at.is_(None))
        .where(UserProfile.is_public.is_(True))
        .where(UserProfile.role != "admin")
    )
    if needle:
        stmt = stmt.where(or_(
            User.username.icontains(needle, autoescape=True),
            UserProfile.display_name.icontains(needle, autoescape=True),
        ))
    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).all()
    return {
        "items": [
            {
                "id": r[0],
                "display_name": resolve_display_name(
                    None if r[3] else r[2], r[0], lang
                ),
                "avatar_url": resolve_avatar_url(r[4], r[5]),
                "level": r[6] or 1,
                "tier": tier_for_level(r[6] or 1),
            }
            for r in rows
        ]
    }


@router.get("/{profile_id}")
async def get_profile(
    profile_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    from services.portal.profiles import _serialize_public
    row = (await db.execute(
        select(UserProfile).where(
            UserProfile.id == profile_id,
            UserProfile.is_public.is_(True),
            UserProfile.account_active.is_(True),
            UserProfile.role != "admin",
        )
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="profile_not_found")
    # Read-only: hide cosmetics no longer unlocked WITHOUT writing to the viewed
    # user's row. A viewer must not mutate the profile they look at — that was a
    # write-on-read + lost-update footgun. The owner's row is cleaned for real
    # when they next open their own profile (/me).
    updates = await _stale_decoration_updates(db, row, row.user_id)
    if updates:
        db.expunge(row)  # detach so the display-only cleanup can never be flushed
        for field, value in updates.items():
            setattr(row, field, value)
    return _serialize_public(row, lang=lang)
