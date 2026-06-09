"""
Statistics service — re-export module.

The code is split into 3 files for maintainability:
  - stats_collector.py   : periodic collection of Emby sessions
  - stats_aggregator.py  : aggregation, queries, charts, exclusions
  - stats_import.py      : import/purge Jellystats

This file re-exports everything for backwards compatibility of existing imports.
"""

# --- Collector ---
from services.stats_collector import (  # noqa: F401
    _item_lib_cache,
    _resolve_library_name,
    collect_active_sessions,
)

# --- Aggregator ---
from services.stats_aggregator import (  # noqa: F401
    get_exclusions,
    add_exclusion,
    remove_exclusion,
    get_detailed_sessions,
    refresh_library_cache,
    get_libraries_stats,
    get_global_totals,
    get_playback_stats,
    get_users_stats,
    get_activity_history,
    get_activity_minimap,
    get_activity_users,
    get_daily_chart_data,
    get_weekly_heatmap,
    get_records,
    get_user_profile,
    hide_user,
    unhide_user,
    delete_user_stats,
    merge_user_stats,
)

# --- Import ---
from services.stats_import import (  # noqa: F401
    import_jellystats_backup,
    purge_jellystats_import,
)
