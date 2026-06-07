"""Portal authentication via Emby."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.proxy import get_client_ip
from core.rate_limit import ip_key, limiter
from core.security import decode_access_token
from api.auth import PORTAL_COOKIE_NAME, _set_portal_jwt_cookie
from api.auth._csrf import ensure_csrf_cookie, rotate_csrf_cookie
from api.portal.deps import get_current_profile
from models.user import User
from models.portal.profile import UserProfile
from services.portal.emby_auth import authenticate_emby_user
from services.portal.profiles import serialize_profile_with_effective_lang
from services.portal.news import get_unread_news
from services.portal.admin import get_portal_flag, get_portal_settings
from services.security import (
    count_recent_failures,
    ensure_not_blocked,
    record_attempt,
    record_failure,
)

EMBY_SHADOW_SKIP_THRESHOLD = 1

logger = logging.getLogger("mediakeeper.portal.auth")
router = APIRouter(prefix="/auth", tags=["portal-auth"])


class PortalLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=500)


async def _serialize_donation(db: AsyncSession) -> dict:
    """Operator-configured donation link surfaced on the heart panel to
    every portal user. ``enabled`` is True only when the operator turned it
    on AND set a link, so the frontend can gate the heart on this alone."""
    s = await get_portal_settings(db)
    url = s.get("portal.donation.url", "")
    enabled = bool(s.get("portal.donation.enabled")) and bool(url)
    return {
        "enabled": enabled,
        "url": url if enabled else "",
        "message": s.get("portal.donation.message", "") if enabled else "",
    }


async def _serialize_ui_flags(db: AsyncSession, profile: UserProfile) -> dict:
    is_admin = profile.role == "admin"
    anonymize_requests = False if is_admin else await get_portal_flag(
        db,
        "portal.anonymize_requests",
    )
    allow_adult_requests = is_admin or await get_portal_flag(
        db,
        "portal.allow_adult_requests",
    )
    return {
        "show_requests_tab": is_admin or not anonymize_requests,
        "allow_adult_requests": allow_adult_requests,
        "donation": await _serialize_donation(db),
    }


async def _safe_serialize_ui_flags(db: AsyncSession, profile: UserProfile) -> dict:
    try:
        return await _serialize_ui_flags(db, profile)
    except Exception:
        # Mirror the full success shape so the frontend never reads an absent
        # flag on the degraded path (fail-closed: the request button stays
        # disabled rather than wrongly enabled).
        return {
            "show_requests_tab": True,
            "allow_adult_requests": False,
            "donation": {"enabled": False, "url": "", "message": ""},
        }


async def _safe_get_unread_news(db: AsyncSession, user_id: int) -> list[dict]:
    try:
        return await get_unread_news(db, user_id)
    except Exception:
        return []


async def _log_login(
    db: AsyncSession,
    user_id: int | None,
    username: str,
    source: str,
    success: bool,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """Best-effort write to the login history table — never blocks the
    auth flow, the audit signal is informational only."""
    try:
        from models.portal.login_history import UserLoginHistory
        db.add(UserLoginHistory(
            user_id=user_id,
            username=(username or "")[:100] or None,
            source=source,
            success=success,
            ip=(ip or "")[:64] or None,
            user_agent=(user_agent or "")[:255] or None,
        ))
        await db.commit()
    except Exception:
        await db.rollback()


@router.post("/login")
@limiter.limit("5/minute", key_func=ip_key)
async def portal_login(
    req: PortalLoginRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate via Emby and issue JWT cookie."""
    client_ip = get_client_ip(request) or "unknown"
    user_agent = request.headers.get("user-agent")
    # Normalize input for brute-force tracking so casing variants resolve to a
    # single rate-limit bucket (mirrors api.auth.login). Raw req.username is
    # kept for Emby auth (its own casing semantics), the enumeration warning
    # log and the login-history row.
    tracking_username = (req.username or "").strip().lower()
    await ensure_not_blocked(db, client_ip, tracking_username, "portal")

    # Shadow-skip Emby once we already recorded a recent failure, so Emby's
    # own lockout on the user account doesn't trip before our block does.
    recent_fails = await count_recent_failures(
        db, client_ip, tracking_username, "portal",
    )
    if recent_fails > EMBY_SHADOW_SKIP_THRESHOLD:
        await record_failure(db, client_ip, tracking_username, "portal", user_agent)
        logger.warning(
            "[PORTAL_LOGIN] Shadow-skip Emby for user=%s ip=%s (fails=%s)",
            req.username, client_ip, recent_fails,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    result = await authenticate_emby_user(db, req.username, req.password)
    if not result:
        await record_failure(db, client_ip, tracking_username, "portal", user_agent)
        await _log_login(db, None, req.username, "portal", False, client_ip, user_agent)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    _set_portal_jwt_cookie(response, result["token"], request)
    rotate_csrf_cookie(response, request)
    await record_attempt(db, client_ip, tracking_username, "portal", success=True, user_agent=user_agent)
    await _log_login(db, result["user"].id, req.username, "portal", True, client_ip, user_agent)

    user = result["user"]
    profile = result["profile"]

    # Stamp the profile with login metadata so the admin "Users" page
    # can surface online state, last IP and last user-agent.
    try:
        from datetime import datetime, timezone
        profile.last_login_at = datetime.now(timezone.utc)
        profile.last_seen_at = profile.last_login_at
        profile.last_login_ip = (client_ip or "")[:64] or None
        profile.last_login_user_agent = (user_agent or "")[:255] or None
        db.add(profile)
        await db.commit()
    except Exception:
        await db.rollback()
    user_id = user.id
    username = user.username
    profile_payload = await serialize_profile_with_effective_lang(db, profile, user=user)
    unread = await _safe_get_unread_news(db, user_id)
    ui_flags = await _safe_serialize_ui_flags(db, profile)

    # Daily login XP (best-effort, 1x per calendar day)
    try:
        from services.portal.xp import grant_daily_login_xp
        await grant_daily_login_xp(db, user_id)
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass

    # Check achievements on login — fire-and-forget so the response is not
    # blocked by an inherently slow scan (5 passes + playback queries). The
    # background task opens its own DB session, which is critical because
    # the request-scoped one is closed once login returns.
    from services.portal.achievements import safe_check_all_achievements_in_new_session
    background_tasks.add_task(
        safe_check_all_achievements_in_new_session,
        user_id,
        username,
        "login",
    )

    return {
        "success": True,
        "profile": profile_payload,
        "unread_news": unread,
        "ui": ui_flags,
    }


@router.get("/me")
async def portal_me(
    request: Request,
    response: Response,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get current portal user info."""
    ensure_csrf_cookie(response, request)
    user, profile = up

    # Bump last_seen_at so the admin "Users" page can drive its online
    # indicator. We only re-write when the previous bump is older than
    # 30s to avoid hammering the DB on a noisy /me poll.
    try:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        previous = profile.last_seen_at
        if previous is None or previous.tzinfo is None or (now - previous) > timedelta(seconds=30):
            profile.last_seen_at = now
            db.add(profile)
            await db.commit()
    except Exception:
        await db.rollback()

    unread = await _safe_get_unread_news(db, user.id)
    return {
        "profile": await serialize_profile_with_effective_lang(db, profile, user=user),
        "unread_news_count": len(unread),
        "ui": await _safe_serialize_ui_flags(db, profile),
        "gdpr": await _safe_serialize_gdpr(db, user),
    }


async def _safe_serialize_gdpr(db: AsyncSession, user: User) -> dict:
    """Expose the toggle + this user's pending deletion timestamp.

    The UI uses ``enabled`` to decide whether to show the Privacy tab,
    and ``pending_deletion_at`` to render the grace-period banner. A DB
    hiccup must not break ``/me`` — fall back to the disabling defaults.
    """
    try:
        from services.portal.gdpr import is_gdpr_enabled
        enabled = await is_gdpr_enabled(db)
    except Exception:
        enabled = False
    pending = getattr(user, "pending_deletion_at", None)
    requested = getattr(user, "deletion_requested_at", None)
    return {
        "enabled": bool(enabled),
        "deletion_requested_at": requested.isoformat() if requested else None,
        "pending_deletion_at": pending.isoformat() if pending else None,
    }


@router.post("/logout")
async def portal_logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Clear the portal cookie and revoke the server-side session.

    Stamps ``user_profiles.tokens_invalidated_at`` so a leaked ``rq_token``
    cannot be replayed after the legitimate owner clicked "logout". The
    handler is intentionally tolerant: a missing or already-revoked
    cookie still returns 200 so the frontend logout flow stays
    idempotent.
    """
    response.delete_cookie(key=PORTAL_COOKIE_NAME, path="/")
    token = request.cookies.get(PORTAL_COOKIE_NAME)
    payload = decode_access_token(token) if token else None
    username = (payload or {}).get("sub")
    if username:
        try:
            user = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one_or_none()
            if user:
                await db.execute(
                    update(UserProfile)
                    .where(UserProfile.user_id == user.id)
                    .values(tokens_invalidated_at=datetime.now(timezone.utc))
                )
                await db.commit()
        except Exception:
            await db.rollback()
    return {"ok": True}
