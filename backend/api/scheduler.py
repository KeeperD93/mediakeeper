"""
Scheduler API — task CRUD + manual trigger.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_csrf
from core.database import get_db
from models.user import User
from models.scheduler_task import SchedulerTask
from services.scheduler import TASK_DEFINITIONS, get_scheduler, get_progress

logger = logging.getLogger("mediakeeper.scheduler_api")
router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class TaskUpdateRequest(BaseModel):
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
    if key not in TASK_DEFINITIONS:
        raise HTTPException(status_code=404, detail="task_unknown")

    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="scheduler_not_initialized")
    if scheduler.is_task_running(key):
        raise HTTPException(status_code=409, detail="task_already_running")

    import asyncio
    asyncio.create_task(scheduler._run_task(key))
    return {"success": True, "message": f"Task {key} started"}
