"""
Scheduler API — task CRUD + manual trigger.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_csrf
from core.database import get_db
from models.user import User
from models.scheduler_task import SchedulerTask, TaskStatus
from services.scheduler import TASK_DEFINITIONS, get_progress

logger = logging.getLogger("mediakeeper.scheduler_api")
router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class TaskUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled:      bool | None = None
    interval_sec: int  | None = None


# ── List all tasks ─────────────────────────────────────────────────

@router.get("/tasks")
async def list_tasks(
    db: AsyncSession  = Depends(get_db),
    _:  User          = Depends(get_current_user),
):
    result = await db.execute(select(SchedulerTask).order_by(SchedulerTask.key))
    rows = result.scalars().all()

    tasks = []
    for row in rows:
        defn = TASK_DEFINITIONS.get(row.key, {})
        prog = get_progress(row.key)
        tasks.append({
            "key":          row.key,
            "label":        row.label,
            "label_key":    defn.get("label_key", ""),
            "description":  defn.get("description", ""),
            "enabled":      row.enabled,
            "interval_sec": row.interval_sec,
            "default_sec":  defn.get("default_sec", row.interval_sec),
            "last_run":     row.last_run.isoformat() if row.last_run else None,
            "last_status":  row.last_status,
            "last_error":   row.last_error,
            "run_count":    row.run_count or 0,
            "progress":     prog,
        })
    return tasks


# ── Update a task ────────────────────────────────────────────────────────

@router.patch("/tasks/{key}")
async def update_task(
    key: str,
    req: TaskUpdateRequest,
    db:  AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _:   User         = Depends(get_current_user),
):
    result = await db.execute(select(SchedulerTask).where(SchedulerTask.key == key))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="task_unknown")

    if req.enabled is not None:
        row.enabled = req.enabled
    if req.interval_sec is not None:
        if req.interval_sec < 10:
            raise HTTPException(status_code=400, detail="interval_min_10_seconds")
        row.interval_sec = req.interval_sec

    await db.commit()
    return {"success": True, "key": key}


# ── Reset to default values ──────────────────────────────────────────────

@router.post("/tasks/{key}/reset")
async def reset_task(
    key: str,
    db:  AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _:   User         = Depends(get_current_user),
):
    defn = TASK_DEFINITIONS.get(key)
    if not defn:
        raise HTTPException(status_code=404, detail="task_unknown")

    result = await db.execute(select(SchedulerTask).where(SchedulerTask.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.interval_sec = defn["default_sec"]
        row.enabled      = defn["default_on"]
        await db.commit()
    return {"success": True, "interval_sec": defn["default_sec"], "enabled": defn["default_on"]}


# ── Manual trigger ──────────────────────────────────────────────────────

@router.post("/tasks/{key}/run")
async def run_task_now(
    key: str,
    db:  AsyncSession = Depends(get_db),
    csrf_protected: None = Depends(require_csrf),
    _:   User         = Depends(get_current_user),
):
    """Request a manual run via inter-process flag.

    In production deployments the API and the scheduler tick in
    different processes (``MK_SEPARATE_BACKGROUND_WORKER=true``), so
    calling ``scheduler._run_task`` from here would no-op — the
    ``_scheduler_instance`` global is ``None`` on the web side. We
    stamp ``force_run_requested_at`` on the row instead; the
    scheduler loop in the worker process polls it every 10 s and
    triggers the run on the next tick.

    When the API and worker share a process (DEBUG mode or
    single-process default), the same mechanism still works — the
    scheduler loop poll picks it up immediately.
    """
    from datetime import datetime, timezone

    if key not in TASK_DEFINITIONS:
        raise HTTPException(status_code=404, detail="task_unknown")

    row = (
        await db.execute(select(SchedulerTask).where(SchedulerTask.key == key))
    ).scalar_one_or_none()
    if row is None:
        # Task definition exists but the row is not seeded yet — the
        # scheduler's ``_ensure_tasks_exist`` startup pass hasn't run.
        raise HTTPException(status_code=503, detail="scheduler_not_initialized")
    if row.last_status == TaskStatus.RUNNING.value:
        raise HTTPException(status_code=409, detail="task_already_running")

    row.force_run_requested_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True, "message": f"Task {key} run requested"}


# ── Cache inspection / management ─────────────────────────────────────
#
# Surfaces the in-memory caches the app maintains so the admin panel
# can render a Seerr-style "Cache" section under the same Settings →
# Scheduler tab. Phase B exposes the TMDB search cache; Phase C will
# add the image and DNS caches by registering them in the same
# ``_CACHES`` registry.


def _list_caches() -> list[dict]:
    """Return one stat snapshot per registered cache.

    The registry is local to this module and intentionally simple —
    new caches expose ``get_cache_stats`` + ``clear_cache`` helpers
    and get listed here. Keeps the API contract stable as caches
    are added in later phases.
    """
    from services.portal import dns_cache, image_cache, tmdb_search

    return [
        {"id": "tmdb", **tmdb_search.get_cache_stats()},
        {"id": "images", **image_cache.get_cache_stats()},
        {"id": "dns", **dns_cache.get_cache_stats()},
    ]


@router.get("/caches")
async def list_caches(
    _: User = Depends(get_current_user),
):
    """Snapshot of every cache for the admin readout."""
    return {"items": _list_caches()}


@router.post("/caches/{cache_id}/clear")
async def clear_cache_endpoint(
    cache_id: str,
    csrf_protected: None = Depends(require_csrf),
    _: User = Depends(get_current_user),
):
    """Drop every entry from the named cache + reset its counters.

    Behaves like Seerr's "Vider le cache" button: the cache rebuilds
    organically on the next user query, no warmup needed.
    """
    from services.portal import dns_cache, image_cache, tmdb_search

    handlers = {
        "tmdb": tmdb_search.clear_cache,
        "images": image_cache.clear_cache,
        "dns": dns_cache.clear_cache,
    }
    handler = handlers.get(cache_id)
    if handler is None:
        raise HTTPException(status_code=404, detail="cache_unknown")
    cleared = handler()
    return {"success": True, "cleared": cleared}
