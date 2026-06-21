"""System routes: health, config, Emby proxy (sessions, logs, images, ...)."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.encryption import get_persistent_fernet_key
from core.http_client import get_internal_client
from core.database import engine, get_db
from core.security import (
    decode_access_token,
    is_backoffice_admin,
    is_token_valid_for_revocation_pivot,
)
from models.settings import Setting
from models.user import User
from models.portal.profile import UserProfile
from services.emby import (
    get_activity_logs,
    get_alerts,
    get_sessions,
    get_streams_count,
    proxy_image,
    proxy_user_image,
    refresh_library,
)
from services.settings import get_active_media_source, get_tools_config
from services.system import get_system_stats

logger = logging.getLogger("mediakeeper")
router = APIRouter()

# Process-scoped identifier so a frontend that survives a backend restart can
# detect the rebuild and force a fresh login (the JWT may be invalidated by
# session rotation or a Fernet key rotation at boot).
BOOT_ID = uuid.uuid4().hex


async def _admin_session_valid(username: str, iat: int | None, db: AsyncSession) -> bool:
    """True iff ``username`` still maps to an active backoffice admin whose
    session predates any force-logout pivot. Mirrors get_current_user's live
    checks (minus its must-change-password UX gate)."""
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    return bool(
        user
        and user.is_active
        and is_backoffice_admin(user.username)
        and is_token_valid_for_revocation_pivot(iat, user.tokens_invalidated_at)
    )


async def _portal_session_valid(username: str, iat: int | None, db: AsyncSession) -> bool:
    """True iff ``username`` maps to an active portal profile whose session
    predates any force-logout pivot. Mirrors get_current_profile's checks."""
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if not user or not user.is_active:
        return False
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    return bool(
        profile
        and profile.account_active
        and is_token_valid_for_revocation_pivot(iat, profile.tokens_invalidated_at)
    )


async def _is_health_full_authorized(request: Request, db: AsyncSession) -> bool:
    """Gate for the infra-exposing ``full`` health variant: a valid, active,
    non-revoked admin session. On any failure the route falls back to the
    public basic payload instead of erroring."""
    from api.auth import COOKIE_NAME

    token = request.cookies.get(COOKIE_NAME)
    payload = decode_access_token(token) if token else None
    if not payload or payload.get("scope") != "admin":
        return False
    username = payload.get("sub")
    if not username:
        return False
    return await _admin_session_valid(username, payload.get("iat"), db)


def register_health_route(app, version: str, is_db_ready_fn) -> None:
    """Register /api/health with the dynamic DB-state check."""

    @app.get("/api/health")
    async def health_check(request: Request, full: bool = Query(default=False)):
        if not is_db_ready_fn():
            return JSONResponse(
                status_code=503,
                content={
                    "status": "starting",
                    "version": version,
                    "database": "initializing",
                    "boot_id": BOOT_ID,
                },
            )
        status = {
            "status": "ok",
            "version": version,
            "database": "ok",
            "boot_id": BOOT_ID,
        }
        # The full variant runs an outbound media-source probe and exposes
        # infra state, so it is gated behind a valid admin session; an
        # unauthenticated caller silently gets the basic payload.
        full_allowed = False
        try:
            async with AsyncSession(engine) as session:
                await session.execute(select(Setting).limit(1))
                full_allowed = full and await _is_health_full_authorized(request, session)
                if full_allowed:
                    media_source = await get_active_media_source(session)
                    if not media_source:
                        status["media_source"] = "not_configured"
                    else:
                        status["media_source"] = media_source["source"]
                        url = (media_source.get("url") or "").rstrip("/")
                        api_key = media_source.get("api_key") or ""
                        if not url or not api_key:
                            status["status"] = "degraded"
                            status["media_source_status"] = "misconfigured"
                        else:
                            try:
                                response = await get_internal_client().get(
                                    f"{url}/System/Info",
                                    headers={"X-Emby-Token": api_key},
                                    timeout=2.0,
                                )
                                if response.is_success:
                                    status["media_source_status"] = "ok"
                                else:
                                    status["status"] = "degraded"
                                    status["media_source_status"] = f"http_{response.status_code}"
                            except Exception:
                                logger.exception("Full health check media source probe failed")
                                status["status"] = "degraded"
                                status["media_source_status"] = "error"
        except Exception:
            status["status"] = "degraded"
            status["database"] = "error"
        if full_allowed and status["status"] != "ok":
            return JSONResponse(status_code=503, content=status)
        return status


@router.get("/api/health/encryption")
async def health_encryption_key(_: User = Depends(get_current_user)):
    """Report the provenance of the at-rest encryption key.

    The admin UI surfaces a persistent banner when this returns
    ``warning: true`` (ephemeral key) so the operator notices that
    every secret stored from now on will be unreadable after a
    container restart.
    """
    persistent = get_persistent_fernet_key()
    if persistent is None:
        return {"persistent": False, "source": "ephemeral", "warning": True}
    return {"persistent": True, "source": persistent.source, "warning": False}


@router.get("/api/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return les URLs des outils actifs for le frontend (iframes sidebar)."""
    tools_config = await get_tools_config(db)
    tools = {}
    for key, cfg in tools_config.items():
        if cfg.get("enabled") and cfg.get("url"):
            tools[key] = cfg["url"]
    return {"tools": tools}


@router.get("/api/stats/system")
async def system_stats(_: User = Depends(get_current_user)):
    return await get_system_stats()


@router.get("/api/emby/sessions")
async def emby_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_sessions(db)


@router.get("/api/emby/logs")
async def emby_logs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_activity_logs(db, limit=20)


@router.get("/api/emby/alerts")
async def emby_alerts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_alerts(db, limit=30)


@router.get("/api/emby/streams")
async def emby_streams(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = await get_streams_count(db)
    return {"count": count}


@router.post("/api/emby/refresh")
async def emby_refresh(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Start a full scan of the Emby library."""
    return await refresh_library(db)


async def _authenticate_media_proxy_request(request: Request, db: AsyncSession) -> str:
    """
    Validate the JWT on image proxy routes against the live account state.

    Accepts both the admin and the portal cookies because posters and avatars
    are consumed by both surfaces; each token must carry an explicit ``scope``
    claim. The backing account is checked for deactivation and force-logout
    (revocation pivot) so a revoked session stops loading images immediately
    instead of riding the JWT to its natural expiry.
    """
    from api.auth import COOKIE_NAME, PORTAL_COOKIE_NAME

    jwt_token = request.cookies.get(COOKIE_NAME) or request.cookies.get(PORTAL_COOKIE_NAME)
    payload = decode_access_token(jwt_token) if jwt_token else None
    scope = payload.get("scope") if payload else None
    if scope not in ("admin", "portal"):
        raise HTTPException(status_code=401, detail="not_authenticated")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="token_invalid")

    iat = payload.get("iat")
    valid = (
        await _admin_session_valid(username, iat, db)
        if scope == "admin"
        else await _portal_session_valid(username, iat, db)
    )
    if not valid:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return username


@router.get("/api/emby/image/{item_id}")
async def emby_image(
    item_id: str,
    request: Request,
    type: str = "Primary",
    db: AsyncSession = Depends(get_db),
):
    """
    Emby image proxy — avoids exposing the api_key to the frontend.
    Auth via cookie httpOnly only.
    """
    await _authenticate_media_proxy_request(request, db)

    result = await proxy_image(db, item_id, image_type=type)
    if not result:
        raise HTTPException(status_code=404, detail="image_not_available")
    image_bytes, content_type = result
    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/api/emby/user-image/{user_id}")
async def emby_user_image(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Proxy image de profil user Emby."""
    await _authenticate_media_proxy_request(request, db)
    result = await proxy_user_image(db, user_id)
    if not result:
        return Response(status_code=204)
    image_bytes, content_type = result
    return Response(
        content=image_bytes,
        media_type=content_type,
        # Short max-age so a user updating their Emby photo sees it
        # reflect within a few minutes across the app instead of being
        # pinned for a week by browser disk cache. The 30 min in-memory
        # cache in ``proxy_user_image`` keeps the load off Emby; the
        # client-side window just bounds the visible staleness.
        headers={"Cache-Control": "private, max-age=300"},
    )
