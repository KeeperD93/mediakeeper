"""Task definitions — label, default interval, handler."""
from datetime import datetime

from ._handlers import (
    _handler_backup,
    _handler_clear_image_cache,
    _handler_cleanup_available_requests,
    _handler_duplicates,
    _handler_emby_full_scan,
    _handler_emby_recent_scan,
    _handler_emby_refresh,
    _handler_expire_users,
    _handler_gdpr_purge,
    _handler_healthcheck,
    _handler_log_cleanup,
    _handler_notifications,
    _handler_quota_recompute,
    _handler_subtitle_auto,
    _handler_watchlist,
)

# default_sec = same duration as the former task hardcoded in main.py
# For tasks without an equivalent (duplicates, emby_refresh): off by default
TASK_DEFINITIONS: dict[str, dict] = {
    "watchlist_scan": {
        "label":       "Scan Watchlist",
        "label_key":   "scheduler.tasks.watchlist_scan",
        "default_sec": 86400,   # 24h
        "default_on":  True,
        "handler":     _handler_watchlist,
        "description": "scheduler.watchlist_check",
    },
    "log_cleanup": {
        "label":       "Log cleanup & collection",
        "label_key":   "scheduler.tasks.log_cleanup",
        "default_sec": 3600,    # 1h
        "default_on":  True,
        "handler":     _handler_log_cleanup,
        "description": "scheduler.log_rotation",
    },
    "notifications": {
        "label":       "Send notifications",
        "label_key":   "scheduler.tasks.notifications",
        "default_sec": 60,      # 1 min
        "default_on":  True,
        "handler":     _handler_notifications,
        "description": "scheduler.notifications",
    },
    "duplicates_scan": {
        "label":       "Duplicate detection",
        "label_key":   "scheduler.tasks.duplicates_scan",
        "default_sec": 86400,
        "default_on":  False,
        "handler":     _handler_duplicates,
        "description": "scheduler.duplicates",
    },
    "emby_refresh": {
        "label":       "Refresh Emby library",
        "label_key":   "scheduler.tasks.emby_refresh",
        "default_sec": 3600,
        "default_on":  False,
        "handler":     _handler_emby_refresh,
        "description": "scheduler.library_scan",
    },
    "backup_auto": {
        "label":       "Automatic backup",
        "label_key":   "scheduler.tasks.backup_auto",
        "default_sec": 86400,
        "default_on":  False,
        "handler":     _handler_backup,
        "description": "scheduler.backup",
    },
    "cleanup_available_requests": {
        "label":       "Auto-cleanup available requests",
        "label_key":   "scheduler.tasks.cleanup_available_requests",
        "default_sec": 86400,   # 24h
        "default_on":  True,    # Gated by ``requests.auto_cleanup_days``:
                                # harmless when 0 (early return, no query).
        "handler":     _handler_cleanup_available_requests,
        "description": "scheduler.cleanup_available_requests",
    },
    "emby_recent_scan": {
        "label":       "Emby Recently Added Scan",
        "label_key":   "scheduler.tasks.emby_recent_scan",
        "default_sec": 300,     # 5 min
        "default_on":  True,
        "handler":     _handler_emby_recent_scan,
        "description": "scheduler.emby_recent_scan",
    },
    "emby_full_scan": {
        "label":       "Emby Full Library Scan",
        "label_key":   "scheduler.tasks.emby_full_scan",
        "default_sec": 7200,    # 2h
        "default_on":  True,
        "handler":     _handler_emby_full_scan,
        "description": "scheduler.emby_full_scan",
    },
    "healthcheck_scan": {
        "label":       "Library health scan",
        "label_key":   "scheduler.tasks.healthcheck_scan",
        "default_sec": 86400,
        "default_on":  False,
        "handler":     _handler_healthcheck,
        "description": "scheduler.healthcheck",
    },
    "subtitle_auto": {
        "label":       "Auto-download subtitles",
        "label_key":   "scheduler.tasks.subtitle_auto",
        "default_sec": 300,     # 5 min
        "default_on":  False,
        "handler":     _handler_subtitle_auto,
        "description": "scheduler.subtitle_auto",
    },
    "expire_users": {
        "label":       "Expire user accounts",
        "label_key":   "scheduler.tasks.expire_users",
        "default_sec": 900,     # 15 min — short enough to feel automatic
                                # without flooding Emby with policy PATCHs.
        "default_on":  True,    # Security-critical: ON by default.
        "handler":     _handler_expire_users,
        "description": "scheduler.expire_users",
    },
    "gdpr_purge": {
        "label":       "GDPR purge of pending deletions",
        "label_key":   "scheduler.tasks.gdpr_purge",
        "default_sec": 86400,   # 24h
        "default_on":  True,    # Gated by ``gdpr.enabled``: harmless
                                # when off (early return, no query).
        "handler":     _handler_gdpr_purge,
        "description": "scheduler.gdpr_purge",
    },
    "quota_auto_recompute": {
        "label":       "Auto request-quota recompute",
        "label_key":   "scheduler.tasks.quota_auto_recompute",
        "default_sec": 3600,    # Hourly check; ``cadence_guard`` lets the
                                # scheduled run act only at ~00:00.
        "default_on":  True,    # Gated: scheduled run only at midnight, no-op
                                # when disabled via quota.auto.enabled or with
                                # no auto rows.
        "handler":     _handler_quota_recompute,
        # Cadence-only gate: the scheduled (interval) run fires hourly but acts
        # only during the local midnight hour. A manual "Run Now" force-run
        # bypasses this and reaches the engine immediately.
        "cadence_guard": lambda: datetime.now().hour == 0,
        "description": "scheduler.quota_auto_recompute",
    },
    "clear_image_cache": {
        "label":       "Clear image cache",
        "label_key":   "scheduler.tasks.clear_image_cache",
        "default_sec": 604800,  # 7 days
        "default_on":  False,   # Opt-in: no automatic purge until the
                                # admin sets a schedule, the disk has
                                # no size cap by design.
        "handler":     _handler_clear_image_cache,
        "description": "scheduler.clear_image_cache",
    },
}
