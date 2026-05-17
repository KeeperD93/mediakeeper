"""Scheduler class: main loop + integration (init / getter)."""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from models.scheduler_task import SchedulerTask

from ._db import _ensure_tasks_exist, _load_tasks, _mark_done, _mark_running
from ._progress import clear_progress, update_progress
from ._tasks import TASK_DEFINITIONS

logger = logging.getLogger("mediakeeper.scheduler")


class Scheduler:
    """
    Dynamic scheduler.
    - Reloads the DB config every 60s
    - Each task runs in its own independent asyncio loop
    - If the interval changes, the loop adapts on the next cycle
    """

    # Lightweight tasks excluded from the sequential queue
    _LIGHTWEIGHT_TASKS = {"notifications", "log_cleanup"}

    def __init__(self, engine: AsyncEngine):
        self._engine = engine
        self._config: dict[str, dict] = {}  # key → {enabled, interval_sec}
        self._timers: dict[str, float] = {}  # key → monotonic instant of the next run
        self._heavy_lock = asyncio.Lock()    # serializes heavy tasks
        self._running_tasks: set[str] = set()
        self._running_lock = asyncio.Lock()

    def is_task_running(self, key: str) -> bool:
        return key in self._running_tasks

    async def _run_task(self, key: str) -> None:
        """Run a handler and update status in the DB.
        Heavy tasks go through a lock so they run one at a time."""
        defn = TASK_DEFINITIONS.get(key)
        if not defn:
            return

        async with self._running_lock:
            if key in self._running_tasks:
                logger.info("[scheduler] Task already running, skipping: %s", key)
                return
            self._running_tasks.add(key)

        try:
            if key in self._LIGHTWEIGHT_TASKS:
                await self._exec_task(key, defn)
            else:
                async with self._heavy_lock:
                    await self._exec_task(key, defn)
        finally:
            async with self._running_lock:
                self._running_tasks.discard(key)

    async def _exec_task(self, key: str, defn: dict) -> None:
        """Actual execution of a task."""
        logger.info(f"[scheduler] Starting task : {key}")
        update_progress(key, 0, 0, "starting")
        async with AsyncSession(self._engine, expire_on_commit=False) as db:
            await _mark_running(db, key)
        error = None
        try:
            async with AsyncSession(self._engine, expire_on_commit=False) as db:
                await defn["handler"](db)
        except Exception as e:
            error = str(e)
            logger.error(f"[scheduler] Task error {key}: {e}", exc_info=True)
            try:
                from services.monitoring import AlertType, send_alert

                await send_alert(
                    AlertType.SCHEDULER_TASK_CRASHED,
                    {"task": key, "error": error[:200]},
                )
            except Exception:
                logger.exception("[scheduler] Failed to push monitoring alert")
        clear_progress(key)
        async with AsyncSession(self._engine, expire_on_commit=False) as db:
            await _mark_done(db, key, error)
        logger.info(f"[scheduler] Task {key} done — {'OK' if not error else 'ERROR'}")

    async def _reload_config(self) -> None:
        """Reload configuration from the DB."""
        try:
            async with AsyncSession(self._engine, expire_on_commit=False) as db:
                self._config = await _load_tasks(db)
        except Exception as e:
            logger.error(f"[scheduler] Error reloading config: {e}")

    async def _init_timers(self) -> None:
        """Initialize timers based on last_run in DB."""
        immediate_tasks = {"notifications", "log_cleanup"}
        now = asyncio.get_event_loop().time()
        now_dt = datetime.now(timezone.utc)

        last_runs: dict[str, datetime | None] = {}
        async with AsyncSession(self._engine, expire_on_commit=False) as db:
            result = await db.execute(select(SchedulerTask))
            for row in result.scalars().all():
                last_runs[row.key] = row.last_run

        for key, cfg in self._config.items():
            interval = cfg.get("interval_sec", 86400)
            if key in immediate_tasks:
                self._timers[key] = now
                continue
            last_run = last_runs.get(key)
            if not last_run:
                self._timers[key] = now + 60
                logger.info(f"[scheduler] {key}: never executed, run in 60s")
                continue
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)
            elapsed = (now_dt - last_run).total_seconds()
            if elapsed >= interval:
                self._timers[key] = now + 60
                logger.info(f"[scheduler] {key} : overdue by {elapsed/3600:.1f}h, run in 60s")
            else:
                remaining = interval - elapsed
                self._timers[key] = now + remaining
                logger.info(f"[scheduler] {key} : next run in {remaining/3600:.1f}h")

    async def run(self) -> None:
        """Main scheduler loop."""
        async with AsyncSession(self._engine, expire_on_commit=False) as db:
            await _ensure_tasks_exist(db)
        await self._reload_config()

        # Startup delay to let the app initialize
        await asyncio.sleep(30)
        await self._init_timers()

        TICK = 10       # check every 10s
        CONFIG_RELOAD = 60  # config reload every 60s
        last_reload = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(TICK)
            now = asyncio.get_event_loop().time()

            if now - last_reload >= CONFIG_RELOAD:
                await self._reload_config()
                last_reload = now

            # Inter-process "Run Now" trigger — the API stamps
            # ``force_run_requested_at`` and we pick it up here. Done
            # before the interval-based pass so a manual click never
            # waits behind a regular tick.
            await self._consume_force_run_requests()

            for key, cfg in self._config.items():
                if not cfg.get("enabled"):
                    continue
                interval = cfg.get("interval_sec", 86400)
                next_run = self._timers.get(key, now)
                if now >= next_run:
                    self._timers[key] = now + interval
                    asyncio.create_task(self._run_task(key))

    async def _consume_force_run_requests(self) -> None:
        """Poll ``force_run_requested_at`` and launch any flagged tasks.

        Reads the column in one shot, clears it in the same
        transaction, then schedules ``_run_task`` for each key
        outside the transaction so a long-running handler doesn't
        block the next tick. ``is_task_running`` guards against
        double-launches when the user double-clicks the button.
        """
        try:
            async with AsyncSession(
                self._engine, expire_on_commit=False
            ) as db:
                rows = (
                    await db.execute(
                        select(SchedulerTask).where(
                            SchedulerTask.force_run_requested_at.isnot(None)
                        )
                    )
                ).scalars().all()
                if not rows:
                    return
                keys = []
                for row in rows:
                    row.force_run_requested_at = None
                    keys.append(row.key)
                await db.commit()
        except Exception as e:  # noqa: BLE001 -- best-effort, log + skip
            logger.error(
                f"[scheduler] force-run poll failed: {e}", exc_info=True
            )
            return

        for key in keys:
            if key not in TASK_DEFINITIONS:
                logger.warning(
                    f"[scheduler] force-run requested for unknown key: {key}"
                )
                continue
            if self.is_task_running(key):
                logger.info(
                    f"[scheduler] force-run skipped (already running): {key}"
                )
                continue
            logger.info(f"[scheduler] force-run launching: {key}")
            asyncio.create_task(self._run_task(key))


# Global instance — initialized in main.py
_scheduler_instance: Scheduler | None = None


def init_scheduler(engine: AsyncEngine) -> Scheduler:
    global _scheduler_instance
    _scheduler_instance = Scheduler(engine)
    return _scheduler_instance


def get_scheduler() -> Scheduler | None:
    return _scheduler_instance
