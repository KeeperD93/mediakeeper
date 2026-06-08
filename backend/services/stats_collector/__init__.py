"""
Statistics service — periodic collection of Emby sessions.
Package split into modules (Rule 9, <= 300 lines).
"""
from ._cache import _item_lib_cache, _normalize_library_name
from ._resolver import _resolve_library_name, _session_library_name
from .collect import collect_active_sessions

__all__ = [
    "_item_lib_cache",
    "_normalize_library_name",
    "_resolve_library_name",
    "_session_library_name",
    "collect_active_sessions",
]
