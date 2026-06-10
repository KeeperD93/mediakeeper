"""
Statistics service — aggregation and queries.
Package split into modules (Rule 9, <= 300 lines).

Legacy imports `from services.stats_aggregator import X` keep working
thanks to the re-exports below.
"""
from .activity import (
    get_activity_grouped,
    get_activity_history,
    get_activity_minimap,
    get_activity_users,
)
from .charts import get_daily_chart_data, get_weekly_heatmap
from .exclusions import _get_exclusion_filters, add_exclusion, get_exclusions, remove_exclusion
from .libraries import get_libraries_stats, refresh_library_cache
from .playback import get_playback_stats
from .profile import get_user_profile
from .records import get_records
from .sessions import get_detailed_sessions
from .totals import get_global_totals
from .users import get_users_stats
from .users_admin import (
    _get_hidden_users,
    _set_hidden_users,
    delete_user_stats,
    hide_user,
    merge_user_stats,
    unhide_user,
)

__all__ = [
    "add_exclusion",
    "delete_user_stats",
    "get_activity_grouped",
    "get_activity_history",
    "get_activity_minimap",
    "get_activity_users",
    "get_daily_chart_data",
    "get_detailed_sessions",
    "get_exclusions",
    "get_global_totals",
    "get_libraries_stats",
    "get_playback_stats",
    "get_records",
    "get_user_profile",
    "get_users_stats",
    "get_weekly_heatmap",
    "hide_user",
    "merge_user_stats",
    "refresh_library_cache",
    "remove_exclusion",
    "unhide_user",
]
