import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from services.portal import strip_tags_and_trim
from services.portal._rank_tiers import tier_for_level
from services.portal.avatars import resolve_avatar_url
from services.portal.profile_serializers import (
    DISPLAY_NAME_LOCK_DAYS as DISPLAY_NAME_LOCK_DAYS,
    display_name_locked_until,
    serialize_profile as serialize_profile,
    serialize_public_profile as _serialize_public,
)
from services.settings import get_portal_default_language

logger = logging.getLogger("mediakeeper.portal.profiles")


async def serialize_profile_with_effective_lang(
    db: AsyncSession, profile: UserProfile, *, user: User | None = None
) -> dict:
    """``serialize_profile`` plus ``effective_language``: the nullable raw
    ``language`` resolved against the instance default. Used by the owner-facing
    surfaces that drive the portal locale (auth /login + /me, profiles /me)."""
    result = serialize_profile(profile, user=user)
    result["effective_language"] = profile.language or await get_portal_default_language(db)
    return result


async def resolve_admin_identity(db: AsyncSession, user_id: int) -> dict:
    """Avatar/level/tier for the backoffice topbar avatar.

    Shared by /auth/me and the admin /portal-login response so both expose
    the same ring data. Without this, the login payload omitted tier/avatar
    and the topbar fell back to the bronze default until the next /me
    (page refresh). ``UserProfile`` is 1:1 with ``User``; the row is ``None``
    for admins who never visited the portal side (→ bronze, level 1)."""
    row = (await db.execute(
        select(
            UserProfile.avatar_url,
            UserProfile.avatar_custom_path,
            UserProfile.level,
        ).where(UserProfile.user_id == user_id)
    )).first()
    level = row.level if row and row.level else 1
    return {
        "avatar_url": resolve_avatar_url(row.avatar_url, row.avatar_custom_path) if row else None,
        "level": level,
        "tier": tier_for_level(level),
    }

MAX_DISPLAY_NAME_RESOLVE_ATTEMPTS = 999

# Reserved display names. Compared case-insensitively. The admin role is
# the only one allowed to keep "admin" — every other user is rejected
# both on PUT /me and from the live availability check.
RESERVED_DISPLAY_NAMES = frozenset({
    "admin", "administrator", "administrateur", "root",
})


def is_reserved_display_name(name: str) -> bool:
    return (name or "").strip().lower() in RESERVED_DISPLAY_NAMES


async def get_or_create_profile(
    db: AsyncSession, user: User
) -> UserProfile:
    """Get existing profile or create one for the user."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        return profile

    base = user.username
    is_admin = user.username == "admin"
    unique_name = await resolve_unique_display_name(db, base, exclude_user_id=user.id)
    profile = UserProfile(
        user_id=user.id,
        display_name=unique_name,
        role="admin" if is_admin else "viewer",
        # The admin account never needs to pick a public username — it is
        # invisible in the leaderboard and not consultable as a profile.
        display_name_must_set=not is_admin,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    logger.info(f"[PROFILE] Created profile for user={user.username} name={unique_name}")
    return profile


async def get_profile_by_user_id(
    db: AsyncSession, user_id: int
) -> UserProfile | None:
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_public_profile(
    db: AsyncSession, profile_id: int, *, lang: str = "fr",
) -> dict | None:
    """Get a public profile by its ID (for other users to view)."""
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.id == profile_id,
            UserProfile.is_public == True,  # noqa: E712
            UserProfile.account_active == True,  # noqa: E712
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return None
    return _serialize_public(profile, lang=lang)


async def is_display_name_taken(
    db: AsyncSession, candidate: str, *, exclude_user_id: int | None = None,
) -> bool:
    """Case-insensitive existence check, optionally ignoring one user."""
    if not candidate:
        return False
    stmt = select(UserProfile.user_id).where(
        func.lower(UserProfile.display_name) == candidate.lower()
    )
    if exclude_user_id is not None:
        stmt = stmt.where(UserProfile.user_id != exclude_user_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def resolve_unique_display_name(
    db: AsyncSession, base: str, *, exclude_user_id: int | None = None,
) -> str:
    """Return ``base`` if free, otherwise ``base2``, ``base3``... until free."""
    candidate = (base or "").strip() or "user"
    if not await is_display_name_taken(db, candidate, exclude_user_id=exclude_user_id):
        return candidate
    for n in range(2, MAX_DISPLAY_NAME_RESOLVE_ATTEMPTS + 1):
        attempt = f"{candidate}{n}"
        if not await is_display_name_taken(db, attempt, exclude_user_id=exclude_user_id):
            return attempt
    raise RuntimeError("Cannot resolve unique display_name after many attempts")


def is_display_name_locked(profile: UserProfile) -> bool:
    until = display_name_locked_until(profile)
    return bool(until and until > datetime.now(timezone.utc))


async def update_profile(
    db: AsyncSession,
    profile: UserProfile,
    data: dict,
    *,
    admin_override: bool = False,
) -> UserProfile:
    """Update profile fields from validated data dict.

    Username rules:
    - Same name (case-insensitive): silently ignored.
    - Locked window (<6 months since last change, ``must_set`` already
      cleared, ``admin_override`` is False): 403 ``display_name_locked``.
    - Already taken by someone else (case-insensitive): 409
      ``display_name_taken``. The endpoint surfaces suggestions via
      ``/me/check-username``; we never silently rewrite a user's choice.
    - First set clears ``must_set`` and stamps ``changed_at``.

    The auto-resolve helper (``resolve_unique_display_name``) is reserved
    for the import path, where the system itself picks a name.
    """
    from fastapi import HTTPException

    allowed = {
        "display_name", "bio", "avatar_url", "avatar_custom_path",
        "favorite_genres", "selected_badges", "selected_title",
        "avatar_effect", "is_public", "language", "hide_adult",
    }
    for key, value in data.items():
        if key not in allowed:
            continue

        if key == "display_name" and isinstance(value, str):
            cleaned = strip_tags_and_trim(value, max_len=50)
            if not cleaned:
                continue
            current_lower = (profile.display_name or "").lower()
            if cleaned.lower() == current_lower:
                # Same name as the current one. If the first-login flag
                # is still pending, treat this submission as an explicit
                # confirmation and clear it — otherwise the modal would
                # reappear on every login because the user "kept" their
                # auto-imported Emby username.
                if profile.display_name_must_set:
                    profile.display_name_must_set = False
                    profile.display_name_changed_at = datetime.now(timezone.utc)
                continue
            if profile.role != "admin" and is_reserved_display_name(cleaned):
                raise HTTPException(status_code=409, detail="display_name_reserved")
            if (
                not admin_override
                and not profile.display_name_must_set
                and is_display_name_locked(profile)
            ):
                raise HTTPException(status_code=403, detail="display_name_locked")
            if await is_display_name_taken(
                db, cleaned, exclude_user_id=profile.user_id,
            ):
                raise HTTPException(status_code=409, detail="display_name_taken")
            profile.display_name = cleaned
            profile.display_name_changed_at = datetime.now(timezone.utc)
            profile.display_name_must_set = False
            continue

        if key == "bio" and isinstance(value, str):
            value = strip_tags_and_trim(value, max_len=500)

        setattr(profile, key, value)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def suggest_display_names(
    db: AsyncSession,
    base: str,
    *,
    exclude_user_id: int | None = None,
    limit: int = 5,
) -> list[str]:
    """Return up to ``limit`` free variants of ``base`` (``base2``, ``base3``...)
    so the UI can offer alternatives when the user picks a taken name."""
    cleaned = (base or "").strip() or "user"
    out: list[str] = []
    n = 2
    while len(out) < limit and n < MAX_DISPLAY_NAME_RESOLVE_ATTEMPTS:
        attempt = f"{cleaned}{n}"
        if not await is_display_name_taken(db, attempt, exclude_user_id=exclude_user_id):
            out.append(attempt)
        n += 1
    return out


async def get_leaderboard(
    db: AsyncSession, limit: int = 20, *, lang: str = "fr",
) -> list[dict]:
    """Top users by XP. Admin accounts are excluded by design."""
    result = await db.execute(
        select(UserProfile)
        .where(
            UserProfile.account_active == True,  # noqa: E712
            UserProfile.is_public == True,  # noqa: E712
            UserProfile.role != "admin",
        )
        .order_by(UserProfile.xp.desc())
        .limit(limit)
    )
    profiles = result.scalars().all()
    return [_serialize_public(p, lang=lang) for p in profiles]


async def add_xp(
    db: AsyncSession, profile: UserProfile, amount: int
) -> UserProfile:
    """Add XP and level up if threshold reached."""
    profile.xp += amount
    new_level = 1 + profile.xp // 100
    if new_level > profile.level:
        profile.level = new_level
        logger.info(f"[PROFILE] user_id={profile.user_id} leveled up to {new_level}")
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
