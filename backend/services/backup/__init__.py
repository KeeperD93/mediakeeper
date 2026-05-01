"""
Service de backup Mediakeeper.
Package split into modules (Rule 9, <= 300 lines). Re-exports for compatibility.

Structure d'un backup :
  mediakeeper_backup_YYYYMMDD_HHMMSS.zip
  ├── manifest.json          — metadata + included components
  ├── settings.json          — config outils (Emby, TMDB…)
  ├── preferences.json       — user preferences
  ├── scheduler.json         — scheduler tasks
  ├── watchlist.json         — watchlist scan data
  ├── pg_dump.sql            — dump PostgreSQL (optionnel)
  └── logs/                  — files de logs (optionnel)
"""
from ._state import (
    DEFAULT_COMPONENTS,
    DEFAULT_RETENTION,
    RETENTION_DAYS_KEY,
    get_current_backup_dir,
)
from .create import create_backup
from .directory import list_available_backup_dirs, set_backup_directory
from .listing import (
    apply_retention,
    apply_retention_by_count,
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
    "create_backup",
    "delete_backup",
    "get_backup_path",
    "get_current_backup_dir",
    "list_available_backup_dirs",
    "list_backups",
    "restore_backup",
    "restore_json_backup",
    "set_backup_directory",
]
