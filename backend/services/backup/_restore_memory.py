"""What a restore aligns in memory once it is saved."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("mediakeeper.backup")


async def apply_restored_settings(db: AsyncSession) -> None:
    """Some settings are held in memory: align them, as saving each on its screen does.
    The restore is already saved, so a failure here is only logged."""
    from core.app_startup import apply_debug_level

    from services.emby import invalidate_emby_config_cache
    from services.media_manager import load_categories
    from services.portal.dns_cache import refresh_from_settings
    from services.portal.image_cache import refresh_enabled_flag
    from services.settings import get_setting
    from services.tmdb import invalidate_tmdb_key_cache

    try:
        invalidate_emby_config_cache()
        invalidate_tmdb_key_cache()
        apply_debug_level(await get_setting(db, "logs.debug_mode") == "true")
        await load_categories(db)
        await refresh_from_settings(db)
        await refresh_enabled_flag(db, force=True)
    except Exception:
        logger.exception("[backup] Restored settings saved, not all applied until the next start")


async def apply_restored_watchlist(db: AsyncSession) -> None:
    """The watchlist screens read a copy held in memory: reload it from the restore.
    The restore is already saved, so a failure here is only logged."""
    from services.watchlist_scanner import _state as watchlist_state

    try:
        watchlist_state.invalidate_calendar_cache()
        watchlist_state.set_cache(None)
        await watchlist_state.ensure_cache_loaded(db)
    except Exception:
        logger.exception("[backup] Restored watchlist saved, not reloaded in memory")
