"""Endpoints /login et /portal-login."""
import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.proxy import get_client_ip
from core.rate_limit import ip_key, limiter
from core.security import (
    create_access_token,
    hash_password,
    is_backoffice_admin,
    is_external_auth_only_password,
    verify_password,
)
from models.portal.profile import UserProfile
from models.user import User
from services.portal.emby_auth import authenticate_emby_user
from services.portal.maintenance import is_maintenance_enabled
from services.portal.profiles import resolve_admin_identity, serialize_profile

from ._cookies import _set_portal_jwt_cookie, _set_jwt_cookie
from ._csrf import rotate_csrf_cookie
from ._portal import (
    _safe_get_unread_news_count,
    _safe_serialize_portal_ui_flags,
    grant_portal_admin_session,
)
from ._schemas import LoginRequest
from services.security import (
    count_recent_failures,
    ensure_not_blocked,
    record_attempt,
    record_failure,
)

# Pre-hashed throwaway password. Verifying an attacker's input against it when
# the username is unknown makes the failed-login path spend the same bcrypt
# time whether or not the account exists, closing the timing oracle (CWE-208).
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


async def _stamp_admin_login(
    db: AsyncSession,
    user: User,
    *,
    client_ip: str | None,
    user_agent: str | None,
) -> None:
    """Mirror what the portal login does: stamp the UserProfile so the
    admin "Users" page can surface a real "last login" entry for local
    backoffice admins (otherwise the profile only sees /me pings)."""
    try:
        profile = (
            await db.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not profile:
            return
        now = datetime.now(timezone.utc)
        profile.last_login_at = now
        profile.last_seen_at = now
        profile.last_login_ip = (client_ip or "")[:64] or None
        profile.last_login_user_agent = (user_agent or "")[:255] or None
        db.add(profile)
        await db.commit()
    except Exception:
        logger.exception("[LOGIN] Profile stamp failed for user_id=%s", user.id)
        await db.rollback()

# Above this many recent portal failures, we stop forwarding the attempt to
# Emby to avoid triggering Emby's own lockout on the target user account.
EMBY_SHADOW_SKIP_THRESHOLD = 1

logger = logging.getLogger("mediakeeper.api.auth")
router = APIRouter()


@router.post("/login")
@limiter.limit("5/minute", key_func=ip_key)
async def login(req: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Authenticate and place the admin JWT in an httpOnly cookie."""
    client_ip = get_client_ip(request) or "unknown"
    user_agent = request.headers.get("user-agent")
    # Normalize input for brute-force tracking so casing variants resolve to a
    # single rate-limit bucket. Raw req.username is kept for failure logs to
    # preserve the enumeration signal an operator can grep.
    tracking_username = (req.username or "").strip().lower()
    await ensure_not_blocked(db, client_ip, tracking_username, "admin")

    result = await db.execute(
        select(User).where(func.lower(User.username) == tracking_username)
    )
    user   = result.scalar_one_or_none()

    if user:
        password_ok = verify_password(req.password, user.hashed_password)
    else:
        # No such user: still run bcrypt so the response time can't reveal it.
        verify_password(req.password, _DUMMY_PASSWORD_HASH)
        password_ok = False

    if not password_ok:
        await record_failure(db, client_ip, tracking_username, "admin", user_agent)
        logger.warning("[LOGIN] Failure for user=%r from %s", req.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    if not user.is_active:
        logger.warning("[LOGIN] Account disabled: %s", req.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_disabled",
        )
    if not is_backoffice_admin(user.username) or is_external_auth_only_password(user.hashed_password):
        await record_failure(db, client_ip, tracking_username, "admin", user_agent)
        logger.warning("[LOGIN] Backoffice refused for user=%r from %s", req.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="backoffice_forbidden",
        )

    token = create_access_token({"sub": user.username, "scope": "admin"})
    _set_jwt_cookie(response, token, request)
    rotate_csrf_cookie(response, request)
    await record_attempt(db, client_ip, tracking_username, "admin", success=True, user_agent=user_agent)
    await _stamp_admin_login(db, user, client_ip=client_ip, user_agent=user_agent)
    # Once authenticated, identify the actor by numeric id rather than
    # username: a successful login no longer needs the PII handle in
    # logs, and an admin can resolve the id from the users table. The
    # FAILURE branches above keep the username clear on purpose so an
    # operator can still spot enumeration / brute-force patterns.
    logger.info("[LOGIN] Success for user_id=%s", user.id)

    return {
        "success":              True,
        "must_change_password":  user.must_change_password,
        "username":              user.username,
    }


@router.post("/portal-login")
@limiter.limit("5/minute", key_func=ip_key)
async def portal_login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Single entry point for the login page.

    - Backoffice accounts keep priority and receive mk_token
      + rq_token to also access the portal module.
    - Imported Emby/Jellyfin accounts only receive rq_token and
      are redirected to the portal on the frontend.
    """
    client_ip = get_client_ip(request) or "unknown"
    user_agent = request.headers.get("user-agent")
    # Same normalization as /login: lower() for brute-force tracking, raw
    # input preserved for logs and for downstream Emby auth which keeps
    # its own casing semantics.
    tracking_username = (req.username or "").strip().lower()
    # Only gate on the admin scope here. The portal scope is gated later,
    # in the cascade branch, so a brute-force attempt on the portal doesn't
    # collaterally lock the admin login from the same IP.
    await ensure_not_blocked(db, client_ip, tracking_username, "admin")

    username = (req.username or "").strip()
    result = await db.execute(
        select(User).where(func.lower(User.username) == tracking_username)
    )
    user = result.scalar_one_or_none()

    # Use canonical username (DB) when the lookup matched so the
    # backoffice gate honours MK_ADMIN_USERS regardless of the casing
    # the user typed. Falls back to the raw input when no DB row
    # matched — keeps the existing Emby cascade behaviour.
    if is_backoffice_admin(user.username if user else username):
        if user:
            local_admin_ok = bool(
                verify_password(req.password, user.hashed_password)
                and not is_external_auth_only_password(user.hashed_password)
            )
        else:
            # Admin-listed username with no account row: run bcrypt anyway so
            # the timing matches a real account with a wrong password.
            verify_password(req.password, _DUMMY_PASSWORD_HASH)
            local_admin_ok = False

        if user and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="account_disabled",
            )

        if local_admin_ok:
            token = create_access_token({"sub": user.username, "scope": "admin"})
            _set_jwt_cookie(response, token, request)
            rotate_csrf_cookie(response, request)
            await grant_portal_admin_session(request, response, user, db)
            await record_attempt(db, client_ip, tracking_username, "admin", success=True, user_agent=user_agent)
            await _stamp_admin_login(db, user, client_ip=client_ip, user_agent=user_agent)
            logger.info("[PORTAL_LOGIN] Admin success for user_id=%s", user.id)
            # Same avatar/level/tier as /auth/me so the topbar rank ring
            # renders on login instead of falling back to bronze until the
            # next /me (page refresh).
            identity = await resolve_admin_identity(db, user.id)
            return {
                "success": True,
                "scope": "admin",
                "must_change_password": user.must_change_password,
                "username": user.username,
                **identity,
            }

        logger.info(
            "[PORTAL_LOGIN] Emby fallback for user=%r "
            "(backoffice credentials invalid or external-only account)",
            username,
        )

    if user and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_disabled",
        )

    # Gate the portal scope here — only callers actually falling into
    # the Emby cascade are subject to portal brute-force blocks.
    await ensure_not_blocked(db, client_ip, tracking_username, "portal")

    # Shadow-skip the Emby call once the caller already has one recent
    # failure on this IP/username pair. Emby maintains its own lockout
    # counter on the target account — forwarding every failed attempt
    # would trigger it before our own block kicks in.
    recent_portal_fails = await count_recent_failures(
        db, client_ip, tracking_username, "portal",
    )
    if recent_portal_fails > EMBY_SHADOW_SKIP_THRESHOLD:
        await record_failure(db, client_ip, tracking_username, "portal", user_agent)
        logger.warning(
            "[PORTAL_LOGIN] Shadow-skip Emby call for user=%s ip=%s (fails=%s)",
            username, client_ip, recent_portal_fails,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    portal_session = await authenticate_emby_user(db, username, req.password)
    if not portal_session:
        await record_failure(db, client_ip, tracking_username, "portal", user_agent)
        logger.warning("[PORTAL_LOGIN] Requests failure for user=%r from %s", username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    portal_user = portal_session["user"]
    # Maintenance mode locks the portal to admins: a member with valid
    # credentials is refused at the door (already-connected members hit the
    # holding page via the router guard). Admins still get in to manage.
    if await is_maintenance_enabled(db) and not is_backoffice_admin(portal_user.username):
        logger.info("[PORTAL_LOGIN] Refused (maintenance) for user_id=%s", portal_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="maintenance",
        )

    _set_portal_jwt_cookie(response, portal_session["token"], request)
    rotate_csrf_cookie(response, request)
    await record_attempt(db, client_ip, tracking_username, "portal", success=True, user_agent=user_agent)

    portal_profile = portal_session["profile"]
    portal_user_id = portal_user.id
    portal_username = portal_user.username
    portal_profile_payload = serialize_profile(portal_profile, user=portal_user)
    unread_count = await _safe_get_unread_news_count(db, portal_user_id)
    ui_flags = await _safe_serialize_portal_ui_flags(db, portal_profile)

    try:
        from services.portal.xp import grant_daily_login_xp
        await grant_daily_login_xp(db, portal_user_id)
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass

    logger.info("[PORTAL_LOGIN] Requests success for user_id=%s", portal_user_id)
    return {
        "success": True,
        "scope": "portal",
        "username": portal_username,
        "profile": portal_profile_payload,
        "unread_news_count": unread_count,
        "ui": ui_flags,
    }
