"""Helpers BDD for le scheduler : creation, loading, statut d'execution."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.scheduler_task import SchedulerTask

from ._tasks import TASK_DEFINITIONS


async def _ensure_tasks_exist(db: AsyncSession) -> None:
    """Insert missing tasks into the DB with default values."""
    for key, defn in TASK_DEFINITIONS.items():
        result = await db.execute(select(SchedulerTask).where(SchedulerTask.key == key))
        if result.scalar_one_or_none() is None:
            db.add(SchedulerTask(
                key          = key,
                label        = defn["label"],
                enabled      = defn["default_on"],
                interval_sec = defn["default_sec"],
            ))
    await db.commit()


async def _load_tasks(db: AsyncSession) -> dict[str, dict]:
    """Charge la config des tasks from la BDD."""
    result = await db.execute(select(SchedulerTask))
    rows = result.scalars().all()
    return {r.key: {"enabled": r.enabled, "interval_sec": r.interval_sec} for r in rows}


async def _mark_running(db: AsyncSession, key: str) -> None:
    row = (await db.execute(select(SchedulerTask).where(SchedulerTask.key == key))).scalar_one_or_none()
    if row:
        row.last_status = "running"
        row.last_run    = datetime.now(timezone.utc)
        await db.commit()


async def _mark_done(db: AsyncSession, key: str, error: str | None = None) -> None:
    row = (await db.execute(select(SchedulerTask).where(SchedulerTask.key == key))).scalar_one_or_none()
    if row:
        row.last_status = "error" if error else "ok"
        row.last_error  = error
        row.run_count   = (row.run_count or 0) + 1
        await db.commit()
