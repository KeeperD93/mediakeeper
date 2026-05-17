"""Task definitions — label, default interval, handler."""
from ._handlers import (
    _handler_backup,
    _handler_clear_image_cache,
    _handler_cleanup_available_requests,
    _handler_duplicates,
    _handler_emby_refresh,
    _handler_expire_users,
    _handler_gdpr_purge,
    _handler_healthcheck,
    _handler_log_cleanup,
    _handler_notifications,
    _handler_subtitle_auto,
    _handler_watchlist,
)

# default_sec = same duration as the former task hardcoded in main.py
# For tasks without an equivalent (duplicates, emby_refresh): off by default
TASK_DEFINITIONS: dict[str, dict] = {
    "watchlist_scan": {
        "label":       "Scan Watchlist",
        "default_sec": 86400,   # 24h
        "default_on":  True,
        "handler":     _handler_watchlist,
        "description": "scheduler.watchlist_check",
    },
    "log_cleanup": {
        "label":       "Log cleanup & collection",
        "default_sec": 3600,    # 1h
        "default_on":  True,
        "handler":     _handler_log_cleanup,
        "description": "scheduler.log_rotation",
    },
    "notifications": {
        "label":       "Send notifications",
        "default_sec": 60,      # 1 min
        "default_on":  True,
        "handler":     _handler_notifications,
        "description": "scheduler.notifications",
    },
    "duplicates_scan": {
        "label":       "Duplicate detection",
        "default_sec": 86400,
        "default_on":  False,
        "handler":     _handler_duplicates,
        "description": "scheduler.duplicates",
    },
    "emby_refresh": {
        "label":       "Refresh Emby library",
        "default_sec": 3600,
        "default_on":  False,
        "handler":     _handler_emby_refresh,
        "description": "scheduler.library_scan",
    },
    "backup_auto": {
        "label":       "Automatic backup",
        "default_sec": 86400,
        "default_on":  False,
        "handler":     _handler_backup,
        "description": "scheduler.backup",
    },
    "cleanup_available_requests": {
        "label":       "Auto-cleanup available requests",
        "default_sec": 86400,   # 24h
        "default_on":  True,    # Gated by ``requests.auto_cleanup_days``:
                                # harmless when 0 (early return, no query).
        "handler":     _handler_cleanup_available_requests,
        "description": "scheduler.cleanup_available_requests",
    },
    "healthcheck_scan": {
        "label":       "Library health scan",
        "default_sec": 86400,
        "default_on":  False,
        "handler":     _handler_healthcheck,
        "description": "scheduler.healthcheck",
    },
    "subtitle_auto": {
        "label":       "Auto-download subtitles",
        "default_sec": 300,     # 5 min
        "default_on":  False,
        "handler":     _handler_subtitle_auto,
        "description": "scheduler.subtitle_auto",
    },
    "expire_users": {
        "label":       "Expire user accounts",
        "default_sec": 900,     # 15 min — short enough to feel automatic
                                # without flooding Emby with policy PATCHs.
        "default_on":  True,    # Security-critical: ON by default.
        "handler":     _handler_expire_users,
        "description": "scheduler.expire_users",
    },
    "gdpr_purge": {
        "label":       "GDPR purge of pending deletions",
        "default_sec": 86400,   # 24h
        "default_on":  True,    # Gated by ``gdpr.enabled``: harmless
                                # when off (early return, no query).
        "handler":     _handler_gdpr_purge,
        "description": "scheduler.gdpr_purge",
    },
    "clear_image_cache": {
        "label":       "Clear image cache",
        "default_sec": 604800,  # 7 days
        "default_on":  False,   # Opt-in: no automatic purge until the
                                # admin sets a schedule, the disk has
                                # no size cap by design.
        "handler":     _handler_clear_image_cache,
        "description": "scheduler.clear_image_cache",
    },
}
