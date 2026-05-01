"""
Emby/Jellyfin service — proxy, sessions, activity, library, images.
Package split into modules (Rule 9, <= 300 lines).

Legacy imports `from services.emby import X` keep working thanks to
the re-exports below.
"""
from .activity import _fetch_activity_entries, get_activity_logs, get_alerts
from .config import (
    ALERT_SEVERITIES,
    ALERT_TYPES,
    _get_emby_config,
    invalidate_emby_config_cache,
)
from .images import proxy_image, proxy_user_image
from .library import fetch_item_by_id, get_duplicates, get_latest_items, refresh_library, search_series_id
from .sessions import get_raw_sessions, get_sessions, get_streams_count

__all__ = [
    "ALERT_SEVERITIES",
    "ALERT_TYPES",
    "fetch_item_by_id",
    "get_activity_logs",
    "get_alerts",
    "get_duplicates",
    "get_latest_items",
    "get_raw_sessions",
    "get_sessions",
    "get_streams_count",
    "invalidate_emby_config_cache",
    "proxy_image",
    "proxy_user_image",
    "refresh_library",
    "search_series_id",
]
