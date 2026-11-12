"""
Statistics service — periodic collection of Emby sessions.
Package split into modules (Rule 9, <= 300 lines).
"""
from ._cache import _item_lib_cache, _normalize_library_name
from ._measure import POLL_INTERVAL_SECONDS, history_measure
from ._resolver import (
    _emby_admin_user_id,
    _fetch_ancestors,
    _match_library_name,
    _resolve_library_name,
    _session_library_name,
)
from ._watch_xp import WATCH_XP_CATCH_UP_SECONDS, catch_up_watch_xp
from .collect import collect_active_sessions

__all__ = [
    "POLL_INTERVAL_SECONDS",
    "WATCH_XP_CATCH_UP_SECONDS",
    "_emby_admin_user_id",
    "_fetch_ancestors",
    "_item_lib_cache",
    "_match_library_name",
    "_normalize_library_name",
    "_resolve_library_name",
    "_session_library_name",
    "catch_up_watch_xp",
    "collect_active_sessions",
    "history_measure",
]
