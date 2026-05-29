import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from models.portal.chat import ChatMessage
from services.logs import fetch_and_store_emby_logs
from services.scheduler import init_scheduler
from services.stats import collect_active_sessions, refresh_library_cache
from services.watchlist import engine_ref as wl_engine_ref

logger = logging.getLogger("mediakeeper")

HEALTH_MONITOR_INTERVAL_SEC = 300
HEALTH_MONITOR_DB_TIMEOUT_SEC = 3.0
# Two consecutive failed pings (~10 minutes) before alerting, to ride
# out brief connectivity blips without spamming the webhook.
HEALTH_MONITOR_FAILURES_BEFORE_ALERT = 2


class BackgroundTaskManager:
    """Orchestrate background loops in a dedicated process."""

    def __init__(self, engine: AsyncEngine):
        self._engine = engine
        self._tasks: list[asyncio.Task] = []
        self._started = False

    async def _supervised(self, name: str, coro_fn, restart_delay: float = 5.0):
        while True:
            try:
                await coro_fn()
            except asyncio.CancelledError:
                logger.info(f"Task {name} cancelled (shutdown)")
                raise
            except Exception as e:
                logger.error(
                    f"Task {name} crashed: {e} — restarting in {restart_delay}s",
                    exc_info=True,
                )
                try:
                    from services.monitoring import AlertType, send_alert

                    await send_alert(
                        AlertType.BACKGROUND_LOOP_CRASHED,
                        {"loop": name, "error": str(e)[:200]},
                    )
                except Exception:
                    logger.exception("Failed to push monitoring alert for loop %s", name)
                await asyncio.sleep(restart_delay)

    async def _run_scheduler(self):
        scheduler = init_scheduler(self._engine)
        await scheduler.run()

    async def _periodic_stats_collection(self):
        await asyncio.sleep(10)
        while True:
            try:
                async with AsyncSession(self._engine, expire_on_commit=False) as session:
                    await collect_active_sessions(session)
            except Exception as e:
                logger.error(f"Error collecte stats: {e}")
            await asyncio.sleep(15)

    async def _periodic_library_cache(self):
        await asyncio.sleep(20)
        try:
            async with AsyncSession(self._engine, expire_on_commit=False) as session:
                await refresh_library_cache(session)
        except Exception as e:
            logger.error(f"Error refresh initial library cache: {e}")

        while True:
            await asyncio.sleep(3600)
            try:
                async with AsyncSession(self._engine, expire_on_commit=False) as session:
                    await refresh_library_cache(session)
            except Exception as e:
                logger.error(f"Error refresh library cache: {e}")

    async def _periodic_emby_index(self):
        await asyncio.sleep(30)
        while True:
            try:
                from services.portal.emby_index import sync_emby_tmdb_index

                async with AsyncSession(self._engine, expire_on_commit=False) as session:
                    result = await sync_emby_tmdb_index(session)
                    logger.info(f"[EMBY_INDEX] Periodic sync: {result}")
            except Exception as e:
                logger.error(f"[EMBY_INDEX] Periodic sync error: {e}")
            await asyncio.sleep(7200)

    async def _periodic_ticket_auto_close(self):
        await asyncio.sleep(180)
        while True:
            try:
                from services.portal.tickets import auto_close_resolved_tickets

                async with AsyncSession(self._engine, expire_on_commit=False) as session:
                    closed = await auto_close_resolved_tickets(session)
                    if closed:
                        logger.info(f"[TICKET_AUTO_CLOSE] Closed {closed} stale ticket(s)")
            except Exception as e:
                logger.error(f"[TICKET_AUTO_CLOSE] error: {e}")
            await asyncio.sleep(21600)  # every 6 hours

    async def _periodic_health_monitor(self):
        """Watch the DB liveness and the connection-pool saturation.

        Runs independently of ``/api/health`` so it still reports during
        startup hiccups, and never relies on the DB to remember its
        debounce state (which lives in :mod:`services.monitoring`).
        """
        from services.monitoring import AlertType, send_alert

        await asyncio.sleep(60)
        consecutive_failures = 0
        last_state_was_down = False
        pool_saturation_streak = 0

        while True:
            db_ok = False
            try:
                async with AsyncSession(self._engine, expire_on_commit=False) as session:
                    await asyncio.wait_for(
                        session.execute(text("SELECT 1")),
                        timeout=HEALTH_MONITOR_DB_TIMEOUT_SEC,
                    )
                db_ok = True
            except Exception as exc:
                consecutive_failures += 1
                logger.warning(
                    "[health_monitor] DB ping failed (%d consecutive): %s",
                    consecutive_failures,
                    exc,
                )

            if db_ok:
                if last_state_was_down:
                    await send_alert(AlertType.DB_RECOVERED, {"after_failures": consecutive_failures})
                    last_state_was_down = False
                consecutive_failures = 0
            elif consecutive_failures >= HEALTH_MONITOR_FAILURES_BEFORE_ALERT and not last_state_was_down:
                await send_alert(
                    AlertType.DB_UNAVAILABLE,
                    {"consecutive_failures": consecutive_failures},
                )
                last_state_was_down = True

            # NullPool (sqlite/tests) exposes no checkout metrics and cannot
            # saturate the way a QueuePool does — skip the probe instead of
            # spinning on AttributeError every tick.
            pool = self._engine.pool
            if hasattr(pool, "checkedout"):
                try:
                    checked_out = pool.checkedout()
                    size = pool.size()
                    overflow = pool.overflow()
                    capacity = size + max(overflow, 0)
                    if capacity > 0 and checked_out >= capacity - 1:
                        pool_saturation_streak += 1
                    else:
                        pool_saturation_streak = 0
                    if pool_saturation_streak >= HEALTH_MONITOR_FAILURES_BEFORE_ALERT:
                        await send_alert(
                            AlertType.POOL_SATURATED,
                            {"checked_out": checked_out, "capacity": capacity},
                        )
                        pool_saturation_streak = 0
                except Exception as exc:
                    logger.debug("[health_monitor] pool inspection failed: %s", exc)

            await asyncio.sleep(HEALTH_MONITOR_INTERVAL_SEC)

    async def _periodic_ws_revocation_sweep(self):
        """Disconnect chat sockets whose JWT was revoked while idle."""
        from api.portal.chat import (
            WS_REVOCATION_CHECK_INTERVAL_SEC,
            prune_revoked_ws_sessions,
        )

        await asyncio.sleep(WS_REVOCATION_CHECK_INTERVAL_SEC)
        while True:
            try:
                async with AsyncSession(self._engine, expire_on_commit=False) as session:
                    closed = await prune_revoked_ws_sessions(session)
                    if closed:
                        logger.info("[ws_revocation] Closed %d revoked socket(s)", closed)
            except Exception as exc:
                logger.error("[ws_revocation] sweep error: %s", exc)
            await asyncio.sleep(WS_REVOCATION_CHECK_INTERVAL_SEC)

    async def _periodic_chat_purge(self):
        await asyncio.sleep(120)
        while True:
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=365)
                async with AsyncSession(self._engine, expire_on_commit=False) as session:
                    result = await session.execute(
                        delete(ChatMessage).where(ChatMessage.created_at < cutoff)
                    )
                    await session.commit()
                    logger.info(f"[CHAT_PURGE] Removed {result.rowcount} messages older than 1y")
            except Exception as e:
                logger.error(f"[CHAT_PURGE] error: {e}")
            await asyncio.sleep(86400)

    async def start(self):
        if self._started:
            return

        wl_engine_ref[0] = self._engine

        try:
            async with AsyncSession(self._engine, expire_on_commit=False) as session:
                await fetch_and_store_emby_logs(session)
        except Exception as e:
            logger.error(f"Error collecte initiale logs Emby: {e}")

        self._tasks = [
            asyncio.create_task(self._supervised("scheduler", self._run_scheduler)),
            asyncio.create_task(self._supervised("stats_collection", self._periodic_stats_collection)),
            asyncio.create_task(self._supervised("library_cache", self._periodic_library_cache)),
            asyncio.create_task(self._supervised("emby_index", self._periodic_emby_index)),
            asyncio.create_task(self._supervised("ticket_auto_close", self._periodic_ticket_auto_close)),
            asyncio.create_task(self._supervised("chat_purge", self._periodic_chat_purge)),
            asyncio.create_task(self._supervised("health_monitor", self._periodic_health_monitor)),
            asyncio.create_task(self._supervised("ws_revocation", self._periodic_ws_revocation_sweep)),
        ]
        self._started = True

    async def stop(self):
        if not self._tasks:
            self._started = False
            return

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._started = False
