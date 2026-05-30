"""Emby/Jellyfin configuration + global cache invalidation."""
import time
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_active_media_source

logger = logging.getLogger("mediakeeper.emby")

# Types considered as alerts (separated from normal activities)
ALERT_TYPES = {
    "user.failed.login",
    "user.passwordchanged",
    "user.locked",
    "user.deleted",
    "user.created",
    "plugin.installed",
    "plugin.updated",
    "plugin.uninstalled",
    "system.update.available",
    "system.update.installed",
    "task.failed",
    "server.restart",
    "server.shutdown",
}
ALERT_SEVERITIES = {"Warning", "Error"}


# ── Cache config (TTL 30s) ────────────────────────────────────────────────────
_emby_config_cache: tuple | None = None  # (url, api_key) or None
_emby_config_cache_ts: float = 0
_EMBY_CONFIG_TTL = 30  # seconds


def _reset_config_cache() -> None:
    global _emby_config_cache, _emby_config_cache_ts
    _emby_config_cache = None
    _emby_config_cache_ts = 0


async def _get_emby_config(db: AsyncSession) -> tuple[str, str] | None:
    """Return ``(url, api_key)`` when the active media source is Emby/Jellyfin,
    or ``None`` when no source is active (or it is Plex).

    Result cached in memory for 30s (avoids ~7 SELECT per page).
    """
    global _emby_config_cache, _emby_config_cache_ts
    now = time.monotonic()
    if _emby_config_cache is not None and (now - _emby_config_cache_ts) < _EMBY_CONFIG_TTL:
        return _emby_config_cache

    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        _emby_config_cache = None
        _emby_config_cache_ts = now
        return None
    url     = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        _emby_config_cache = None
        _emby_config_cache_ts = now
        return None
    _emby_config_cache = (url, api_key)
    _emby_config_cache_ts = now
    return _emby_config_cache


def invalidate_emby_config_cache():
    """Invalidate the Emby config cache + every derived cache."""
    from . import images, sessions

    _reset_config_cache()
    sessions._reset_sessions_cache()
    images._reset_image_caches()
