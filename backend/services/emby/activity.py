"""Emby/Jellyfin activity log (normal activities + alerts)."""
import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client

from .config import ALERT_SEVERITIES, ALERT_TYPES, _get_emby_config

logger = logging.getLogger("mediakeeper.emby")


_RAW_TTL = 10  # seconds — shared TTL for both logs and alerts
_RAW_LIMIT = 200  # fetch the widest window once, partition client-side
_raw_entries_cache: list | None = None
_raw_entries_cache_ts: float = 0
_raw_entries_lock = asyncio.Lock()


def _reset_activity_cache() -> None:
    """Reset the activity cache — used by tests."""
    global _raw_entries_cache, _raw_entries_cache_ts
    _raw_entries_cache = None
    _raw_entries_cache_ts = 0


async def _get_raw_entries(db: AsyncSession) -> list:
    """Fetch the Emby activity log once and share it between logs/alerts consumers."""
    global _raw_entries_cache, _raw_entries_cache_ts

    now = time.monotonic()
    if _raw_entries_cache is not None and (now - _raw_entries_cache_ts) < _RAW_TTL:
        return _raw_entries_cache

    async with _raw_entries_lock:
        now = time.monotonic()
        if _raw_entries_cache is not None and (now - _raw_entries_cache_ts) < _RAW_TTL:
            return _raw_entries_cache

        cfg = await _get_emby_config(db)
        if not cfg:
            return _raw_entries_cache or []

        url, api_key = cfg
        try:
            client = get_internal_client()
            res = await client.get(
                f"{url}/System/ActivityLog/Entries",
                params={"Limit": _RAW_LIMIT},
                headers={"X-Emby-Token": api_key},
            )
            if res.status_code != 200:
                logger.warning(f"_fetch_activity_entries: Emby HTTP {res.status_code}")
                return _raw_entries_cache or []
            items = res.json().get("Items", [])
            _raw_entries_cache = items
            _raw_entries_cache_ts = time.monotonic()
            return items
        except Exception as e:
            logger.error(f"Error _fetch_activity_entries: {e}")
            return _raw_entries_cache or []


async def _fetch_activity_entries(
    db: AsyncSession,
    *,
    include_alerts: bool,
    limit: int,
) -> list:
    """
    Partition the shared activity log.
    - include_alerts=False: normal activities (excludes alerts)
    - include_alerts=True : alerts only
    """
    items = await _get_raw_entries(db)

    result = []
    for item in items:
        t = item.get("Type", "")
        s = item.get("Severity", "")
        is_alert = t in ALERT_TYPES or s in ALERT_SEVERITIES

        if include_alerts and not is_alert:
            continue
        if not include_alerts and is_alert:
            continue

        entry = {
            "date":     item.get("Date", ""),
            "name":     item.get("Name", ""),
            "type":     t,
            "user":     item.get("UserName", ""),
            "severity": s,
        }
        if include_alerts:
            entry["id"]       = str(item.get("Id", ""))
            entry["overview"] = item.get("Overview", "")

        result.append(entry)
        if len(result) >= limit:
            break

    return result


async def get_activity_logs(db: AsyncSession, limit: int = 20):
    """Fetch the normal activities — excluding system alerts."""
    return await _fetch_activity_entries(db, include_alerts=False, limit=limit)


async def get_alerts(db: AsyncSession, limit: int = 30):
    """Fetch les true alertes : failures auth, plugins, errors system."""
    return await _fetch_activity_entries(db, include_alerts=True, limit=limit)
