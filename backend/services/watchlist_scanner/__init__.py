"""
Watchlist Scanner service — Emby/TMDB scans, series analysis, calendar.
Package split into modules (Rule 9, <= 300 lines).

`services.watchlist_scanner._cache` reste accessible dynamicment via le
the `__getattr__` below (used by api/watchlist.py for direct cache access).
"""
from . import _state
from ._emby import _get_all_emby_series, _get_emby_episodes, get_series_libraries
from ._state import (
    engine_ref,
    ensure_cache_loaded,
    get_scan_results,
    get_scan_status,
    invalidate_calendar_cache,
)
from ._tmdb import _h
from .calendar import get_calendar, refresh_calendar_month
from .scan import full_scan, incremental_scan, run_background_scan


def __getattr__(name):
    """Dynamically expose the mutable state (_cache, _calendar_cache) from _state."""
    if name == "_cache":
        return _state.get_cache()
    if name == "_calendar_cache":
        return _state._calendar_cache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "_get_all_emby_series",
    "_get_emby_episodes",
    "_h",
    "engine_ref",
    "ensure_cache_loaded",
    "full_scan",
    "get_calendar",
    "get_scan_results",
    "get_scan_status",
    "get_series_libraries",
    "incremental_scan",
    "invalidate_calendar_cache",
    "refresh_calendar_month",
    "run_background_scan",
]
