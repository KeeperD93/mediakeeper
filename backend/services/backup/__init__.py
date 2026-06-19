"""
MediaKeeper backup service.
Package split into modules (<= 300 lines). Re-exports for compatibility.

Backup structure:
  mediakeeper_backup_YYYYMMDD_HHMMSS.zip
  ├── manifest.json          — metadata + included components
  ├── settings.json          — tool config (Emby, TMDB…)
  ├── preferences.json       — user preferences
  ├── scheduler.json         — scheduler tasks
  ├── watchlist.json         — watchlist scan data
  ├── pg_dump.sql            — PostgreSQL dump (optional)
  └── logs/                  — log files (optional)
"""
from ._state import (
    DEFAULT_COMPONENTS,
    DEFAULT_RETENTION,
    RETENTION_DAYS_KEY,
    resolve_backup_dir,
)
from .create import create_backup
from .directory import list_available_backup_dirs, set_backup_directory
from .listing import (
    apply_retention,
    apply_retention_by_count,
    apply_retention_for_setting,
    delete_backup,
    get_backup_path,
    list_backups,
)
from .restore import restore_backup, restore_json_backup

__all__ = [
    "DEFAULT_COMPONENTS",
    "DEFAULT_RETENTION",
    "RETENTION_DAYS_KEY",
    "apply_retention",
    "apply_retention_by_count",
    "apply_retention_for_setting",
    "create_backup",
    "delete_backup",
    "get_backup_path",
    "list_available_backup_dirs",
    "list_backups",
    "resolve_backup_dir",
    "restore_backup",
    "restore_json_backup",
    "set_backup_directory",
]
