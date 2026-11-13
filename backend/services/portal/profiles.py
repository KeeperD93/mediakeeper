import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import display_name as dn
from models.portal.profile import UserProfile
from models.user import User
from services.portal import strip_tags_and_trim
from services.portal._rank_tiers import tier_for_level
from services.portal.admin_users_constants import ROLE_ADMIN, ROLE_VIEWER
from services.portal.avatars import resolve_avatar_url
from services.portal.display_name_rules import (
    clean_display_name,
    is_display_name_taken,
    judge_display_name,
)
from services.portal.profile_serializers import (
    DISPLAY_NAME_LOCK_DAYS as DISPLAY_NAME_LOCK_DAYS,
)
from services.portal.profile_serializers import (
    serialize_profile as serialize_profile,
)
from services.portal.profile_serializers import (
    serialize_public_profile as _serialize_public,
)
from services.settings import get_portal_default_language

logger = logging.getLogger("mediakeeper.portal.profiles")


async def serialize_profile_with_effective_lang(
    db: AsyncSession, profile: UserProfile, *, user: User | None = None
) -> dict:
    """``serialize_profile`` plus ``effective_language``: the nullable raw
    ``language`` resolved against the instance default. Used by the owner-facing
    surfaces that drive the portal locale (portal /me, profiles /me)."""
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
        role=ROLE_ADMIN if is_admin else ROLE_VIEWER,
        # The admin account never needs to pick a public username — it is
        # invisible in the leaderboard and not consultable as a profile.
        display_name_must_set=not is_admin,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    logger.info("[PROFILE] Created profile for user=%s name=%s", user.username, unique_name)
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


async def resolve_unique_display_name(
    db: AsyncSession, base: str, *, exclude_user_id: int | None = None,
) -> str:
    """Return ``base`` if free, otherwise ``base2``, ``base3``... until free.

    Best-effort only: the check-then-insert window is not serialized and
    there is no DB-level uniqueness constraint on ``display_name`` (only
    ``user_id`` is unique). Two concurrent provisionings of the same base
    can both read "free" and store the same name. Tolerated by design — a
    duplicate is cosmetic (``user_id`` stays the identity), and for
    unconfirmed accounts the stored value is not even shown (the per-viewer
    pseudo is regenerated live). The user-set path (``update_profile``)
    additionally rejects an already-taken name with a 409.
    """
    candidate = (base or "").strip() or "user"
    if not await is_display_name_taken(db, candidate, exclude_user_id=exclude_user_id):
        return candidate
    for n in range(2, MAX_DISPLAY_NAME_RESOLVE_ATTEMPTS + 1):
        attempt = f"{candidate}{n}"
        if not await is_display_name_taken(db, attempt, exclude_user_id=exclude_user_id):
            return attempt
    raise RuntimeError("Cannot resolve unique display_name after many attempts")


async def update_profile(
    db: AsyncSession,
    profile: UserProfile,
    data: dict,
    *,
    admin_override: bool = False,
) -> UserProfile:
    """Update profile fields from validated data dict.

    A display name goes through ``judge_display_name``: kept as is when it is
    the current one, saved when free, otherwise refused with the HTTP status of
    ``REFUSAL_STATUS`` and ``display_name_<verdict>`` (the endpoint surfaces
    suggestions via ``/me/check-username``; a user's choice is never silently
    rewritten). A first set clears ``must_set`` and stamps ``changed_at``.

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

        if key == "display_name":
            # A name is replaced, never removed: null is ignored like an empty name.
            cleaned = clean_display_name(value) if isinstance(value, str) else ""
            if not cleaned:
                continue
            verdict = await judge_display_name(
                db, profile, cleaned, admin_override=admin_override,
            )
            if verdict == dn.CURRENT:
                continue
            if verdict != dn.FREE:
                raise HTTPException(
                    status_code=dn.REFUSAL_STATUS[verdict], detail=f"display_name_{verdict}",
                )
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
            UserProfile.role != ROLE_ADMIN,
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
        logger.info("[PROFILE] user_id=%s leveled up to %s", profile.user_id, new_level)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
