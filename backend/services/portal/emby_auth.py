"""Authenticate portal users via Emby API."""
import logging

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.security import MEDIA_SERVER_NOT_CONFIGURED, MEDIA_SERVER_UNREACHABLE
from core.http_client import get_internal_client
from core.security import create_access_token
from models.user import User
from models.user_preferences import UserPreference
from models.portal.profile import UserProfile
from services.emby.users import email_from_emby_user
from services.settings import get_active_media_source

logger = logging.getLogger("mediakeeper.portal.emby_auth")

# Only these say the server itself is down. Any other refusal counts as a wrong
# password: a status left uncounted would let a guesser try passwords without limit.
_SERVER_DOWN_STATUSES = frozenset({502, 503, 504})


class MediaServerUnavailable(Exception):
    """The media server could not judge the password: there is no guess to count."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AccountInactive(Exception):
    """The media server accepted the password of an account disabled or expired here."""


def _authenticated_user(res: httpx.Response) -> dict | None:
    """The user named by a 200 answer. Without one, this is not the media server
    talking (a proxy's page, say), and nobody has been authenticated."""
    try:
        body = res.json()
    except ValueError:
        return None
    emby_user = body.get("User") if isinstance(body, dict) else None
    if not isinstance(emby_user, dict):
        return None
    emby_user_id = emby_user.get("Id")
    return emby_user if emby_user_id and isinstance(emby_user_id, str) else None


async def _imported_account(
    db: AsyncSession, emby_user_id: str, username: str
) -> tuple[User, UserProfile] | None:
    """The MediaKeeper account of this media-server user, by the server's own id
    first: a name can change there, and not every database lower-cases an accented
    capital the way Python does. Older profiles only have the name."""
    by_id = (await db.execute(
        select(User, UserProfile)
        .join(UserProfile, UserProfile.user_id == User.id)
        .where(UserProfile.emby_user_id == emby_user_id)
    )).all()
    if len(by_id) == 1:
        return by_id[0][0], by_id[0][1]
    if by_id:
        # A rename followed by the id sync can link two profiles to one server
        # account: only the name typed can tell which, never a guess.
        for user, profile in by_id:
            if user.username.lower() == username.lower():
                return user, profile
        logger.warning("[EMBY_AUTH] Login refused: %r matches none of a shared id's profiles", username)
        return None

    # Lookup case-insensitive so a user typing any casing matches the
    # canonical username stored in the DB (Emby itself is case-insensitive
    # on login, so the lookup here must follow suit).
    result = await db.execute(
        select(User).where(func.lower(User.username) == username.lower())
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("[EMBY_AUTH] Login refused: %r not imported", username)
        return None

    prof_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = prof_result.scalar_one_or_none()
    if not profile:
        logger.warning("[EMBY_AUTH] Login refused: %r has no profile", username)
        return None
    return user, profile


async def authenticate_emby_user(
    db: AsyncSession, username: str, password: str
) -> dict | None:
    """
    Authenticate against Emby API.
    Returns {"token": jwt, "user": User, "profile": UserProfile}, or None for a
    refused password or an account never imported or never activated, which must
    read the same. Raises MediaServerUnavailable or AccountInactive for the cases
    told apart.
    """
    source = await get_active_media_source(db) or {}
    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if source.get("source") not in ("emby", "jellyfin") or not url or not api_key:
        logger.warning("[EMBY_AUTH] No media server configured")
        raise MediaServerUnavailable(MEDIA_SERVER_NOT_CONFIGURED)

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
        # Whatever stopped the call (network, a bad address or key), nothing judged the password.
        logger.error("[EMBY_AUTH] Connection error: %s", e)
        raise MediaServerUnavailable(MEDIA_SERVER_UNREACHABLE) from e

    if res.status_code in _SERVER_DOWN_STATUSES:
        logger.error("[EMBY_AUTH] Media server down (HTTP %s)", res.status_code)
        raise MediaServerUnavailable(MEDIA_SERVER_UNREACHABLE)
    if res.status_code != 200:
        logger.warning("[EMBY_AUTH] Failed for user=%r (HTTP %s)", username, res.status_code)
        return None

    emby_user = _authenticated_user(res)
    if emby_user is None:
        logger.error("[EMBY_AUTH] A 200 answer named no user")
        raise MediaServerUnavailable(MEDIA_SERVER_UNREACHABLE)
    emby_user_id = emby_user["Id"]

    # --- Security gate --------------------------------------------------
    # Users MUST be pre-imported by an admin before they can log in.
    # We deliberately do NOT auto-create User / UserProfile rows here —
    # that was the old "just-in-time" provisioning flow and it let
    # any Emby user self-provision a Portal account, which is not what
    # we want. Import first, activate, then login.
    account = await _imported_account(db, emby_user_id, username)
    if account is None:
        return None
    user, profile = account

    # Emby may still accept the password of an account disabled here.
    if not user.is_active or not profile.account_active:
        # Seen watching or imported, but never let in: told apart, the page would
        # confirm the password of anyone on the media server. Switching an account
        # off stamps this date.
        if profile.tokens_invalidated_at is None:
            logger.warning("[EMBY_AUTH] Login refused: %r never activated", username)
            return None
        logger.warning("[EMBY_AUTH] Disabled account: %r", username)
        raise AccountInactive

    # Catch profiles whose access window has elapsed but that the
    # scheduler hasn't processed yet (cold start, paused task, etc.).
    # Deactivates Emby + MK in-place so the very next login is rejected
    # by the ``account_active`` gate above.
    from .admin_users_expiration import expire_profile_if_due
    if await expire_profile_if_due(db, profile, user):
        logger.warning("[EMBY_AUTH] Expired account: %r", username)
        raise AccountInactive

    # Keep the avatar in sync with Emby on every successful login so
    # admins see the right picture when browsing the user list.
    needs_commit = False
    if not profile.avatar_url:
        profile.avatar_url = f"/api/emby/user-image/{emby_user_id}"
        db.add(profile)
        needs_commit = True
    # Backfill the Emby GUID on profiles that pre-date migration 035, so
    # the admin enable/disable toggle has a target.
    if not profile.emby_user_id:
        profile.emby_user_id = emby_user_id
        db.add(profile)
        needs_commit = True
    # Fill the email from Emby Connect on first sight; never clobber an
    # address an admin typed in manually.
    if not profile.email:
        emby_email = email_from_emby_user(emby_user)
        if emby_email:
            profile.email = emby_email
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
    logger.info("[EMBY_AUTH] Success for user_id=%s", user.id)

    return {"token": token, "user": user, "profile": profile}
