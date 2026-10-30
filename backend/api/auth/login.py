"""Endpoints /login and /portal-login."""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.security import UNKNOWN_CLIENT_IP
from core.database import get_db
from core.proxy import get_client_ip
from core.rate_limit import ip_key, limiter
from core.security import (
    EXTERNAL_AUTH_PASSWORD_SENTINEL,
    create_access_token,
    hash_password,
    is_backoffice_admin,
    is_external_auth_only_password,
    verify_password,
)
from models.user import User
from services.portal.emby_auth import authenticate_emby_user
from services.portal.maintenance import is_maintenance_enabled
from services.portal.profiles import resolve_admin_identity, serialize_profile

from ._cookies import _set_portal_jwt_cookie, _set_jwt_cookie
from ._csrf import rotate_csrf_cookie
from ._portal import (
    _safe_get_unread_news_count,
    _safe_serialize_portal_ui_flags,
    _stamp_admin_login,
    grant_portal_admin_session,
)
from ._schemas import LoginRequest
from services.security import (
    ensure_not_blocked,
    record_failure,
    record_success,
)

# Pre-hashed throwaway password. Verifying an attacker's input against it when
# the username is unknown makes the failed-login path spend the same bcrypt
# time whether or not the account exists, closing the timing oracle (CWE-208).
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))

logger = logging.getLogger("mediakeeper.api.auth")
router = APIRouter()


def _local_password_ok(password: str, user: User | None) -> bool:
    """The local password check, with bcrypt run even for an unknown name. The
    placeholder of imported accounts is public: typed, it is a wrong password."""
    if user is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        return False
    return verify_password(password, user.hashed_password) and password != EXTERNAL_AUTH_PASSWORD_SENTINEL


@router.post("/login")
@limiter.limit("5/minute", key_func=ip_key)
async def login(req: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Authenticate and place the admin JWT in an httpOnly cookie."""
    client_ip = get_client_ip(request) or UNKNOWN_CLIENT_IP
    user_agent = request.headers.get("user-agent")
    # Normalize input for brute-force tracking so casing variants resolve to a
    # single rate-limit bucket. Raw req.username is kept for failure logs to
    # preserve the enumeration signal an operator can grep.
    tracking_username = req.username.strip().lower()
    await ensure_not_blocked(db, client_ip, tracking_username, "admin")

    result = await db.execute(
        select(User).where(func.lower(User.username) == tracking_username)
    )
    user   = result.scalar_one_or_none()

    if not _local_password_ok(req.password, user):
        await record_failure(db, client_ip, tracking_username, "admin", user_agent)
        logger.warning("[LOGIN] Failure for user=%r from %s", req.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    if not user.is_active:
        logger.warning("[LOGIN] Account disabled: %r", req.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_disabled",
        )
    # The password is right: refusing the backoffice is no guess to count.
    if not is_backoffice_admin(user.username):
        logger.warning("[LOGIN] Backoffice refused for user=%r from %s", req.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="backoffice_forbidden",
        )

    # Read before the profile stamp: a failed stamp rolls the session back.
    user_id, username, must_change = user.id, user.username, user.must_change_password
    token = create_access_token({"sub": username, "scope": "admin"})
    _set_jwt_cookie(response, token, request)
    rotate_csrf_cookie(response, request)
    await record_success(db, client_ip, tracking_username, "admin", user_agent)
    await _stamp_admin_login(db, user, client_ip=client_ip, user_agent=user_agent)
    # Once authenticated, identify the actor by numeric id rather than
    # username: a successful login no longer needs the PII handle in
    # logs, and an admin can resolve the id from the users table. The
    # FAILURE branches above keep the username clear on purpose so an
    # operator can still spot enumeration / brute-force patterns.
    logger.info("[LOGIN] Success for user_id=%s", user_id)

    return {
        "success":              True,
        "must_change_password":  must_change,
        "username":              username,
    }


async def _admin_signed_in(
    request: Request,
    response: Response,
    db: AsyncSession,
    user: User,
    *,
    client_ip: str,
    tracking_username: str,
    user_agent: str | None,
) -> dict:
    """Backoffice and portal sessions for an admin whose local password matched."""
    # Read before the profile stamp: a failed stamp rolls the session back.
    user_id, username, must_change = user.id, user.username, user.must_change_password
    token = create_access_token({"sub": username, "scope": "admin"})
    _set_jwt_cookie(response, token, request)
    rotate_csrf_cookie(response, request)
    await grant_portal_admin_session(request, response, user, db)
    await record_success(db, client_ip, tracking_username, "admin", user_agent)
    await _stamp_admin_login(db, user, client_ip=client_ip, user_agent=user_agent)
    logger.info("[PORTAL_LOGIN] Admin success for user_id=%s", user_id)
    # Same avatar/level/tier as /auth/me so the topbar rank ring renders on
    # login instead of falling back to bronze until the next /me (page refresh).
    identity = await resolve_admin_identity(db, user_id)
    return {
        "success": True,
        "scope": "admin",
        "must_change_password": must_change,
        "username": username,
        **identity,
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
    client_ip = get_client_ip(request) or UNKNOWN_CLIENT_IP
    user_agent = request.headers.get("user-agent")
    # Same normalization as /login: lower() for brute-force tracking; the
    # trimmed name keeps its letter case for logs and for downstream Emby
    # auth, which has its own casing semantics.
    tracking_username = req.username.strip().lower()
    # Only gate on the admin scope here. The portal scope is gated later,
    # in the cascade branch, so a brute-force attempt on the portal doesn't
    # collaterally lock the admin login from the same IP.
    await ensure_not_blocked(db, client_ip, tracking_username, "admin")

    username = req.username.strip()
    result = await db.execute(
        select(User).where(func.lower(User.username) == tracking_username)
    )
    user = result.scalar_one_or_none()

    # Use canonical username (DB) when the lookup matched so the
    # backoffice gate honours MK_ADMIN_USERS regardless of the casing
    # the user typed. Falls back to the typed name when no DB row
    # matched — keeps the existing Emby cascade behaviour.
    admin_listed = is_backoffice_admin(user.username if user else username)
    if admin_listed:
        if _local_password_ok(req.password, user):
            if not user.is_active:
                logger.warning("[PORTAL_LOGIN] Account disabled for user=%r from %s", username, client_ip)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="account_disabled",
                )
            return await _admin_signed_in(
                request, response, db, user,
                client_ip=client_ip, tracking_username=tracking_username, user_agent=user_agent,
            )
        logger.info(
            "[PORTAL_LOGIN] Emby fallback for user=%r "
            "(backoffice credentials invalid or external-only account)",
            username,
        )

    # A refused try at an admin's local password counts in the admin scope, which
    # only a local success clears: knowing the Emby password must not reset it.
    # An imported account has no local password, only its Emby one to protect.
    # The dummy hash stands in for a missing account: same bcrypt time either way.
    imported = admin_listed and is_external_auth_only_password(
        user.hashed_password if user else _DUMMY_PASSWORD_HASH
    )
    local_password_guessed = bool(admin_listed and user and not imported)
    failure_scope = "admin" if local_password_guessed else "portal"
    try:
        # Only callers falling into the Emby cascade face portal blocks.
        await ensure_not_blocked(db, client_ip, tracking_username, "portal")
    except HTTPException:
        if local_password_guessed:
            await record_failure(db, client_ip, tracking_username, "admin", user_agent)
        raise

    portal_session = await authenticate_emby_user(db, username, req.password)
    if not portal_session:
        await record_failure(db, client_ip, tracking_username, failure_scope, user_agent)
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
    await record_success(db, client_ip, tracking_username, "portal", user_agent)

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
