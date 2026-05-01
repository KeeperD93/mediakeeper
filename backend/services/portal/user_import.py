"""
Import Emby users into the Portal as pre-created (inactive) profiles.

Rationale: we want admins to pre-provision every Portal account before
the user's first login, so unknown Emby users cannot self-register.
``authenticate_emby_user`` refuses any login whose ``User`` row doesn't
already exist, so this import is the only way to create them.

Imported profiles default to:
- ``account_active = False``  — admin must activate them explicitly
- ``role = "viewer"``          — no privilege by default
- avatar mirrored from Emby    — for the admin UI
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.user import User
from models.user_preferences import UserPreference
from models.portal.profile import UserProfile
from services.portal.profiles import resolve_unique_display_name
from services.settings import get_active_media_source

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
        select(User).where(User.username == emby_username)
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


async def import_emby_users(db: AsyncSession) -> dict:
    """
    Fetch every user from Emby's ``/Users`` endpoint and create a
    matching MediaKeeper User + UserProfile for each one that doesn't
    exist yet. Existing rows are left untouched (we only fill in the
    avatar if it's missing, and refresh the display_name).

    Returns counters ``{created, updated, skipped, total_emby}``.
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return {"error": "no_source"}

    url = (source.get("url") or "").rstrip("/")
    api_key = source.get("api_key") or ""
    if not url or not api_key:
        return {"error": "no_config"}

    client = get_internal_client()
    try:
        res = await client.get(
            f"{url}/Users",
            headers={"X-Emby-Token": api_key},
        )
    except Exception as e:
        logger.error(f"[USER_IMPORT] network error: {e}")
        return {"error": "network"}

    if res.status_code != 200:
        logger.warning(f"[USER_IMPORT] HTTP {res.status_code}")
        return {"error": f"http_{res.status_code}"}

    emby_users = res.json() or []
    created = 0
    updated = 0
    skipped = 0
    usernames = {eu.get("Name") or "" for eu in emby_users if eu.get("Name")}

    existing_users_by_name: dict[str, User] = {}
    if usernames:
        existing_users = (
            await db.execute(select(User).where(User.username.in_(usernames)))
        ).scalars().all()
        existing_users_by_name = {user.username: user for user in existing_users}

    existing_profiles_by_user_id: dict[int, UserProfile] = {}
    if existing_users_by_name:
        existing_profiles = (
            await db.execute(
                select(UserProfile).where(
                    UserProfile.user_id.in_(
                        [user.id for user in existing_users_by_name.values()]
                    )
                )
            )
        ).scalars().all()
        existing_profiles_by_user_id = {
            profile.user_id: profile for profile in existing_profiles
        }

    for eu in emby_users:
        emby_name = eu.get("Name") or ""
        emby_id = eu.get("Id") or ""
        if not emby_name:
            skipped += 1
            continue

        # 1. Ensure a MediaKeeper User row exists (login key = Emby name)
        user_row = existing_users_by_name.get(emby_name)
        if not user_row:
            user_row = User(
                username=emby_name,
                hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
                is_active=True,
                must_change_password=False,
            )
            db.add(user_row)
            await db.flush()
            existing_users_by_name[emby_name] = user_row

        # 2. Ensure a UserProfile row exists for that User
        profile = existing_profiles_by_user_id.get(user_row.id)

        avatar_url = f"/api/emby/user-image/{emby_id}" if emby_id else None

        if not profile:
            unique_name = await resolve_unique_display_name(
                db, emby_name, exclude_user_id=user_row.id,
            )
            profile = UserProfile(
                user_id=user_row.id,
                display_name=unique_name,
                avatar_url=avatar_url,
                role="viewer",
                source="emby",
                emby_user_id=emby_id or None,
                account_active=False,  # <- security: admin activates manually
                display_name_must_set=True,
            )
            db.add(profile)
            existing_profiles_by_user_id[user_row.id] = profile
            db.add(UserPreference(user_id=user_row.id))
            created += 1
        else:
            # Only the avatar is mirrored from Emby on subsequent imports —
            # the display_name belongs to the user once it's been set in
            # MediaKeeper and we never overwrite their customization.
            if avatar_url and profile.avatar_url != avatar_url:
                profile.avatar_url = avatar_url
                updated += 1
            else:
                skipped += 1

    await db.commit()
    logger.info(
        f"[USER_IMPORT] {created} created, {updated} updated, "
        f"{skipped} unchanged (out of {len(emby_users)} Emby users)"
    )
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total_emby": len(emby_users),
    }
