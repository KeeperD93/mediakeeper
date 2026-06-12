"""
Lazily provision MediaKeeper accounts for Emby users.

``authenticate_emby_user`` refuses any login whose ``User`` row doesn't
already exist, so accounts must be created up front. The playback
collector calls ``ensure_user_for_emby_session`` when it observes an
Emby user watching content, creating an inactive profile so XP and
trophies accumulate before that user ever signs in.

Provisioned profiles default to:
- ``account_active = False``  — admin must activate them explicitly
- ``role = "viewer"``          — no privilege by default
- avatar mirrored from Emby    — for the admin UI
"""
import logging
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.user import User
from models.user_preferences import UserPreference
from models.portal.profile import UserProfile
from services.portal.profiles import resolve_unique_display_name

logger = logging.getLogger("mediakeeper.portal.user_import")


async def ensure_user_for_emby_session(
    db: AsyncSession,
    *,
    emby_username: str,
    emby_user_id: str | None = None,
) -> User | None:
    """Lazily provision a MediaKeeper account for an Emby user we observe
    watching content. Used by the playback collector so XP and trophies
    accumulate even if the admin never ran the manual import — the user
    can sign in later and find their progress already stamped.

    Created users land with ``account_active=False`` (the admin still has
    to flip the switch to allow portal login) and ``must_set=True`` so
    the first-login modal asks them for a real display name. Returns the
    user row or ``None`` when the input is malformed.
    """
    if not emby_username:
        return None

    if emby_user_id:
        existing_by_emby_id = (await db.execute(
            select(User)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(UserProfile.emby_user_id == emby_user_id)
            .order_by(UserProfile.account_active.desc(), User.id.asc())
            .limit(1)
        )).scalar_one_or_none()
        if existing_by_emby_id:
            return existing_by_emby_id

    existing = (await db.execute(
        select(User).where(func.lower(User.username) == emby_username.lower())
    )).scalar_one_or_none()
    if existing:
        if emby_user_id:
            profile = (await db.execute(
                select(UserProfile).where(UserProfile.user_id == existing.id)
            )).scalar_one_or_none()
            if profile and not profile.emby_user_id:
                profile.emby_user_id = emby_user_id
                if not profile.avatar_url:
                    profile.avatar_url = f"/api/emby/user-image/{emby_user_id}"
                if not profile.source:
                    profile.source = "emby"
                db.add(profile)
                await db.commit()
        return existing

    user = User(
        username=emby_username,
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.flush()

    avatar_url = f"/api/emby/user-image/{emby_user_id}" if emby_user_id else None
    unique_name = await resolve_unique_display_name(
        db, emby_username, exclude_user_id=user.id,
    )
    profile = UserProfile(
        user_id=user.id,
        display_name=unique_name,
        avatar_url=avatar_url,
        role="viewer",
        source="emby",
        emby_user_id=emby_user_id or None,
        account_active=False,
        display_name_must_set=True,
    )
    db.add(profile)
    db.add(UserPreference(user_id=user.id))
    await db.commit()
    await db.refresh(user)
    logger.info(
        "[USER_IMPORT] lazy-provisioned user from Emby playback: "
        f"username={emby_username} emby_id={emby_user_id}"
    )
    return user
