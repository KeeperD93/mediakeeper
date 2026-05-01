"""
Service settings — package split into modules (Rule 9, <= 300 lines).
"""
from ._emby_urls import (
    _emby_server_id_cache,
    build_emby_deep_link,
    get_emby_public_url,
    get_emby_server_id,
)
from ._kv import (
    get_admin_locale,
    get_all_settings,
    get_notification_channel,
    get_setting,
    get_settings_map,
    get_user_preferences,
    get_watchlist_data,
    encrypt_legacy_sensitive_values,
    set_notification_channel,
    set_setting,
    set_settings_map,
    set_watchlist_data,
    upsert_user_preferences,
)
from ._tools import get_active_media_source, get_tools_config
from ._tools_def import TOOLS_DEFINITION

__all__ = [
    "TOOLS_DEFINITION",
    "get_setting",
    "get_settings_map",
    "set_setting",
    "set_settings_map",
    "get_all_settings",
    "encrypt_legacy_sensitive_values",
    "get_user_preferences",
    "upsert_user_preferences",
    "get_admin_locale",
    "get_watchlist_data",
    "set_watchlist_data",
    "get_notification_channel",
    "set_notification_channel",
    "get_tools_config",
    "get_active_media_source",
    "get_emby_public_url",
    "get_emby_server_id",
    "build_emby_deep_link",
    "_emby_server_id_cache",
]
