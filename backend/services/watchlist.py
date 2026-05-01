"""
Watchlist service — re-export module.

The code is split into 2 files for maintainability:
  - watchlist_scanner.py   : Emby/TMDB scan, series analysis, calendar
  - watchlist_tracking.py  : tracking, ignored list, TMDB search

This file re-exports everything for backwards compatibility of existing imports.
"""

# --- Scanner ---
from services.watchlist_scanner import (  # noqa: F401
    engine_ref,
    get_series_libraries,
    full_scan,
    incremental_scan,
    get_scan_results,
    get_scan_status,
    run_background_scan,
    get_calendar,
    refresh_calendar_month,
    invalidate_calendar_cache,
)

# --- Tracking ---
from services.watchlist_tracking import (  # noqa: F401
    get_ignored,
    add_ignored,
    remove_ignored,
    get_tracked,
    add_tracked,
    remove_tracked,
    search_tmdb_multi,
)
