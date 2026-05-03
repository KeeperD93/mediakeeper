"""System routes: health, config, Emby proxy (sessions, logs, images, ...)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.http_client import get_internal_client
from core.database import engine, get_db
from core.security import decode_access_token
from models.settings import Setting
from models.user import User
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


def register_health_route(app, version: str, is_db_ready_fn) -> None:
    """Register /api/health with the dynamic DB-state check."""

    @app.get("/api/health")
    async def health_check(full: bool = Query(default=False)):
        if not is_db_ready_fn():
            return JSONResponse(
                status_code=503,
                content={"status": "starting", "version": version, "database": "initializing"},
            )
        status = {"status": "ok", "version": version, "database": "ok"}
        try:
            async with AsyncSession(engine) as session:
                await session.execute(select(Setting).limit(1))
                if full:
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
        if full and status["status"] != "ok":
            return JSONResponse(status_code=503, content=status)
        return status


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


def _authenticate_media_proxy_request(request: Request) -> str:
    """
    Validate the JWT on image proxy routes without hitting the DB
    for every poster/avatar loaded.

    Accepts both the admin and the portal cookies because posters and
    avatars are consumed by both surfaces, but each token must carry an
    explicit ``scope`` claim — a JWT without a scope is rejected so a
    forged or migrated-out-of-scope token cannot ride image routes.
    """
    from api.auth import COOKIE_NAME, PORTAL_COOKIE_NAME

    jwt_token = request.cookies.get(COOKIE_NAME)
    if not jwt_token:
        jwt_token = request.cookies.get(PORTAL_COOKIE_NAME)

    payload = decode_access_token(jwt_token) if jwt_token else None
    if not payload or payload.get("scope") not in ("admin", "portal"):
        raise HTTPException(status_code=401, detail="not_authenticated")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="token_invalid")
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
    _authenticate_media_proxy_request(request)

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
    _authenticate_media_proxy_request(request)
    result = await proxy_user_image(db, user_id)
    if not result:
        return Response(status_code=204)
    image_bytes, content_type = result
    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=604800"},
    )
