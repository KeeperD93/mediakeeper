import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from models.portal.chat import ChatMessage
from services.logs import fetch_and_store_emby_logs
from services.scheduler import init_scheduler
from services.stats import collect_active_sessions, refresh_library_cache
from services.watchlist import engine_ref as wl_engine_ref

logger = logging.getLogger("mediakeeper")


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
