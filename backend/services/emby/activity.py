"""Emby/Jellyfin activity log (normal activities + alerts)."""
import asyncio
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.portal.profile import UserProfile

from .config import ALERT_SEVERITIES, ALERT_TYPES, _get_emby_config
from .users import list_emby_users

logger = logging.getLogger("mediakeeper.emby")


_RAW_TTL = 10  # seconds — shared TTL for both logs and alerts
_RAW_LIMIT = 200  # fetch the widest window once, partition client-side
_raw_entries_cache: list | None = None
_raw_entries_cache_ts: float = 0
_raw_entries_lock = asyncio.Lock()

_USER_NAME_TTL = 300  # Emby UserId -> name; names are near-immutable.
_user_name_cache: dict[str, str] = {}
_user_name_cache_ts: float = 0
_user_name_lock = asyncio.Lock()


def _reset_activity_cache() -> None:
    """Reset the activity caches — used by tests."""
    global _raw_entries_cache, _raw_entries_cache_ts
    global _user_name_cache, _user_name_cache_ts
    _raw_entries_cache = None
    _raw_entries_cache_ts = 0
    _user_name_cache = {}
    _user_name_cache_ts = 0


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
                logger.warning("_get_raw_entries: Emby HTTP %s", res.status_code)
                return _raw_entries_cache or []
            items = res.json().get("Items", [])
            _raw_entries_cache = items
            _raw_entries_cache_ts = time.monotonic()
            return items
        except Exception as e:
            logger.error("_get_raw_entries error: %s", e)
            return _raw_entries_cache or []


async def _resolve_user_names(db: AsyncSession, ids: set[str]) -> dict[str, str]:
    """Map Emby ``UserId`` -> display name.

    Emby's ActivityLog carries ``UserId`` (never ``UserName``), so the name is
    resolved here: MediaKeeper profiles first (one query, no Emby round-trip),
    then a single ``/Users`` bulk call for Emby-only accounts. Cached for
    ``_USER_NAME_TTL`` since names are near-immutable; the lock keeps concurrent
    pollers from racing on the cache or firing redundant lookups.
    """
    global _user_name_cache, _user_name_cache_ts
    async with _user_name_lock:
        now = time.monotonic()
        if (now - _user_name_cache_ts) >= _USER_NAME_TTL:
            _user_name_cache = {}
            _user_name_cache_ts = now

        missing = {i for i in ids if i and i not in _user_name_cache}
        if missing:
            rows = (
                await db.execute(
                    select(UserProfile.emby_user_id, UserProfile.display_name)
                    .where(UserProfile.emby_user_id.in_(missing))
                )
            ).all()
            for emby_id, name in rows:
                _user_name_cache[emby_id] = name
            still_missing = missing - _user_name_cache.keys()
            if still_missing:
                # One /Users bulk call instead of one GET per id.
                emby_names = {
                    u.get("Id"): u.get("Name", "") for u in await list_emby_users(db)
                }
                for uid in still_missing:
                    _user_name_cache[uid] = emby_names.get(uid, "")

        return {i: _user_name_cache.get(i, "") for i in ids}


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

    selected = []
    for item in items:
        t = item.get("Type", "")
        s = item.get("Severity", "")
        is_alert = t in ALERT_TYPES or s in ALERT_SEVERITIES

        if include_alerts and not is_alert:
            continue
        if not include_alerts and is_alert:
            continue

        selected.append(item)
        if len(selected) >= limit:
            break

    names = await _resolve_user_names(
        db, {item.get("UserId", "") for item in selected if item.get("UserId")}
    )

    result = []
    for item in selected:
        entry = {
            "date":     item.get("Date", ""),
            "name":     item.get("Name", ""),
            "type":     item.get("Type", ""),
            "user":     names.get(item.get("UserId", ""), ""),
            "severity": item.get("Severity", ""),
        }
        if include_alerts:
            entry["id"]       = str(item.get("Id", ""))
            entry["overview"] = item.get("Overview", "")
        result.append(entry)

    return result


async def get_activity_logs(db: AsyncSession, limit: int = 20):
    """Fetch the normal activities — excluding system alerts."""
    return await _fetch_activity_entries(db, include_alerts=False, limit=limit)


async def get_alerts(db: AsyncSession, limit: int = 30):
    """Fetch the alerts only: auth failures, plugin issues, system errors."""
    return await _fetch_activity_entries(db, include_alerts=True, limit=limit)
