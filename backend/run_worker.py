import asyncio
import logging
import signal

from core.app_startup import apply_runtime_settings, init_db, prime_watchlist_cache, setup_logging
from core.database import engine
from core.http_client import close_clients, init_clients
from services.background_tasks import BackgroundTaskManager
from services.logs import rotate_logs_if_needed
from services.subtitle_sources.opensubtitles_source import OpenSubtitlesSource
from services.subtitle_sources.registry import register_source

setup_logging()
logger = logging.getLogger("mediakeeper.worker")


async def _wait_for_shutdown_signal() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _mark_stop():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _mark_stop)

    await stop_event.wait()


async def main() -> None:
    manager = BackgroundTaskManager(engine)

    await init_clients()
    await init_db()
    register_source(OpenSubtitlesSource())
    rotate_logs_if_needed()
    await apply_runtime_settings()
    await prime_watchlist_cache()

    logger.info("Mediakeeper background worker started")
    await manager.start()

    try:
        await _wait_for_shutdown_signal()
    finally:
        await manager.stop()
        await close_clients()
        logger.info("Mediakeeper background worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
