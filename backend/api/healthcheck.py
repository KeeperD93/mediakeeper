"""
HealthCheck API — health of media libraries.
"""
import json
import asyncio
import logging
from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.async_utils import safe_create_task
from core.database import get_db, engine as async_engine
from api.auth import get_current_user, require_csrf
from models.user import User
from services.healthcheck import (
    run_healthcheck,
    get_healthcheck_summary,
    get_healthcheck_issues,
    get_healthcheck_grouped,
    get_healthcheck_poster_details,
    get_scan_status,
    DEFAULT_CONFIG,
)
from services.settings import get_setting, set_setting

logger = logging.getLogger("mediakeeper.api.healthcheck")

router = APIRouter(prefix="/api/healthcheck", tags=["healthcheck"])

HEALTHCHECK_CONFIG_KEY = "healthcheck_config"
_scan_launch_lock = asyncio.Lock()
_scan_task: asyncio.Task | None = None


class HealthCheckConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obsolete_codecs_enabled: bool = True
    obsolete_containers_enabled: bool = True
    low_resolution_enabled: bool = True
    min_resolution_height: int = 720
    low_bitrate_enabled: bool = True
    min_video_bitrate_kbps: int = 1000
    no_audio_enabled: bool = True
    large_file_enabled: bool = True
    max_file_size_gb: int = 50
    hdr_no_sdr_enabled: bool = True


@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the health threshold configuration."""
    raw = await get_setting(db, HEALTHCHECK_CONFIG_KEY)
    if raw:
        try:
            return {**DEFAULT_CONFIG, **json.loads(raw)}
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
    return {**DEFAULT_CONFIG}


@router.put("/config")
async def update_config(
    config: HealthCheckConfig,
    db: AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    """Update the health threshold configuration."""
    await set_setting(db, HEALTHCHECK_CONFIG_KEY, json.dumps(config.dict()))
    return {"success": True}


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Overall health score + counters."""
    return await get_healthcheck_summary(db)


@router.get("/issues")
async def issues(
    cursor: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    severity: str = Query(""),
    library: str = Query(""),
    issue_type: str = Query(""),
    extension: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Paginated list of detected issues."""
    return await get_healthcheck_issues(
        db, cursor=cursor, limit=limit,
        severity=severity, library=library, issue_type=issue_type,
        extension=extension,
    )


@router.get("/grouped")
async def grouped(
    severity: str | None = Query(None),
    library: str | None = Query(None),
    issue_type: str | None = Query(None),
    extension: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return all posters (series + movies) with the exact total of issues."""
    return {"items": await get_healthcheck_grouped(
        db,
        severity=severity,
        library=library,
        issue_type=issue_type,
        extension=extension,
    )}


@router.get("/poster/{kind}/{key}")
async def poster_details(
    kind: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Full details of a poster (all related issues)."""
    if kind not in ("series", "movie"):
        return {"items": []}
    return await get_healthcheck_poster_details(db, kind, key)


async def _run_scan_background():
    """Start le scan in sa propre session DB (background task)."""
    from sqlalchemy.ext.asyncio import AsyncSession as AS
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(async_engine, class_=AS, expire_on_commit=False)
    async with async_session() as db:
        try:
            await run_healthcheck(db)
        except Exception as e:
            logger.exception("[healthcheck] Background scan error: %s", e)


@router.post("/scan")
async def scan(
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    """Start a health scan in the background."""
    global _scan_task
    async with _scan_launch_lock:
        status = get_scan_status()
        if status["running"] or (_scan_task and not _scan_task.done()):
            raise HTTPException(status_code=409, detail="scan_already_running")

        _scan_task = safe_create_task(_run_scan_background(), name="healthcheck.scan")
    return {"success": True, "message": "scan_started"}


@router.get("/status")
async def status(
    _: User = Depends(get_current_user),
):
    """Status of the running scan."""
    return get_scan_status()
