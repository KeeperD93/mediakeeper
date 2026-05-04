"""Shared mutable state of the watchlist scanner (scan cache + calendar + engine ref)."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_watchlist_data

logger = logging.getLogger("mediakeeper.watchlist.scanner")

# engine reference injected from main.py
engine_ref: list = [None]

# In-memory cache (DB mirror, loaded at startup)
_cache: dict | None = None   # {"series": [...], "total_missing": N, "total_upcoming": N}
_calendar_cache: dict = {}   # {"YYYY-MM": [...items...]}
_scan_guard = asyncio.Lock()
_scan_meta = {
    "running": False,
    "mode": "",
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def set_cache(data: dict | None) -> None:
    global _cache
    _cache = data


def get_cache() -> dict | None:
    return _cache


async def _load_from_db(db: AsyncSession) -> dict | None:
    global _cache
    if _cache:
        return _cache
    raw = await get_watchlist_data(db, "scan_results")
    if raw:
        try:
            _cache = json.loads(raw)
            return _cache
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
    return None


async def ensure_cache_loaded(db: AsyncSession) -> None:
    """Load the cache from the DB if it is not already in memory."""
    await _load_from_db(db)


async def get_scan_results(db: AsyncSession) -> dict:
    """Return the latest scan results (from cache or DB)."""
    data = await _load_from_db(db)
    if data:
        return data
    return {"series": [], "total_missing": 0, "total_upcoming": 0, "scan_time": 0}


def get_scan_status() -> dict:
    """Return the cache summary without hitting the DB."""
    base = {
        "running": _scan_meta["running"],
        "mode": _scan_meta["mode"],
        "started_at": _scan_meta["started_at"],
        "finished_at": _scan_meta["finished_at"],
        "error": _scan_meta["error"],
    }
    if not _cache:
        return {**base, "ready": False, "total_missing": 0, "total_upcoming": 0}
    return {
        **base,
        "ready": True,
        "total_missing": _cache.get("total_missing", 0),
        "total_upcoming": _cache.get("total_upcoming", 0),
        "series_count": len(_cache.get("series", [])),
    }


def invalidate_calendar_cache() -> None:
    """Empty the in-memory calendar cache (after adding/removing a tracked item)."""
    _calendar_cache.clear()


async def try_start_scan(mode: str) -> bool:
    async with _scan_guard:
        if _scan_meta["running"]:
            return False
        _scan_meta.update(
            running=True,
            mode=mode,
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=None,
            error=None,
        )
        return True


def finish_scan(*, error: str | None = None) -> None:
    _scan_meta.update(
        running=False,
        finished_at=datetime.now(timezone.utc).isoformat(),
        error=error,
    )
