"""Authenticate portal users via Emby API."""
import logging
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from core.security import (
    EXTERNAL_AUTH_PASSWORD_SENTINEL,
    hash_password,
    create_access_token,
)
from models.user import User
from models.user_preferences import UserPreference
from models.portal.profile import UserProfile
from services.settings import get_active_media_source

logger = logging.getLogger("mediakeeper.portal.emby_auth")


async def authenticate_emby_user(
    db: AsyncSession, username: str, password: str
) -> dict | None:
    """
    Authenticate against Emby API.
    Returns {"token": jwt, "user": User, "profile": UserProfile} or None.
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return None

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return None

    client = get_internal_client()
    try:
        res = await client.post(
            f"{url}/Users/AuthenticateByName",
            json={"Username": username, "Pw": password},
            headers={
                "X-Emby-Token": api_key,
                "Content-Type": "application/json",
            },
        )
    except Exception as e:
        logger.error(f"[EMBY_AUTH] Connection error: {e}")
        return None

    if res.status_code != 200:
        logger.warning(f"[EMBY_AUTH] Failed for user={username} (HTTP {res.status_code})")
        return None

    emby_data = res.json()
    emby_user = emby_data.get("User", {})
    emby_user_id = emby_user.get("Id", "")

    # --- Security gate --------------------------------------------------
    # Users MUST be pre-imported by an admin before they can log in.
    # We deliberately do NOT auto-create User / UserProfile rows here —
    # that was the old "just-in-time" provisioning flow and it let
    # any Emby user self-provision a Portal account, which is not what
    # we want. Import first, activate, then login.
    # Lookup case-insensitive so a user typing any casing matches the
    # canonical username stored in the DB (Emby itself is case-insensitive
    # on login, so the lookup here must follow suit).
    result = await db.execute(
        select(User).where(func.lower(User.username) == username.lower())
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"[EMBY_AUTH] Login refused: {username} not imported")
        return None

    prof_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = prof_result.scalar_one_or_none()
    if not profile:
        logger.warning(f"[EMBY_AUTH] Login refused: {username} has no profile")
        return None

    if not profile.account_active:
        logger.warning(f"[EMBY_AUTH] Disabled account: {username}")
        return None

    # Catch profiles whose access window has elapsed but that the
    # scheduler hasn't processed yet (cold start, paused task, etc.).
    # Deactivates Emby + MK in-place so the very next login is rejected
    # by the ``account_active`` gate above.
    from .admin_users_expiration import expire_profile_if_due
    if await expire_profile_if_due(db, profile, user):
        logger.warning(f"[EMBY_AUTH] Expired account: {username}")
        return None

    # Keep the avatar in sync with Emby on every successful login so
    # admins see the right picture when browsing the user list.
    needs_commit = False
    if emby_user_id and not profile.avatar_url:
        profile.avatar_url = f"/api/emby/user-image/{emby_user_id}"
        db.add(profile)
        needs_commit = True
    # Backfill the Emby GUID on profiles that pre-date migration 035, so
    # the admin enable/disable toggle has a target.
    if emby_user_id and not profile.emby_user_id:
        profile.emby_user_id = emby_user_id
        db.add(profile)
        needs_commit = True

    # Backfill a UserPreference row on first login if none exists yet
    # (covers pre-import users or rows created before this safeguard).
    pref_exists = (await db.execute(
        select(UserPreference.id).where(UserPreference.user_id == user.id)
    )).scalar_one_or_none()
    if not pref_exists:
        db.add(UserPreference(user_id=user.id))
        needs_commit = True

    if needs_commit:
        await db.commit()

    token = create_access_token({"sub": user.username, "scope": "portal"})
    # Authenticated path: log the numeric user id instead of the
    # PII-bearing username. Failure branches above keep the username
    # clear on purpose for enumeration / brute-force diagnostics.
    logger.info(f"[EMBY_AUTH] Success for user_id={user.id}")

    return {"token": token, "user": user, "profile": profile}


async def _find_or_create_user(
    db: AsyncSession, username: str
) -> User:
    """Find existing user or create a portal user account."""
    result = await db.execute(
        select(User).where(func.lower(User.username) == username.lower())
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        username=username,
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"[EMBY_AUTH] Created local user for emby user={username}")
    return user


async def _find_or_create_profile(
    db: AsyncSession,
    user: User,
    display_name: str,
    emby_user_id: str,
    emby_url: str,
) -> UserProfile:
    """Find or create user profile, update avatar URL from Emby."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    avatar_url = (
        f"/api/emby/user-image/{emby_user_id}" if emby_user_id else None
    )

    if profile:
        if not profile.avatar_url and avatar_url:
            profile.avatar_url = avatar_url
        db.add(profile)
        await db.commit()
        return profile

    profile = UserProfile(
        user_id=user.id,
        display_name=display_name,
        avatar_url=avatar_url,
        role="viewer",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
