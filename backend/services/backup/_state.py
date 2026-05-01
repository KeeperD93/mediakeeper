"""Constants + backup destination directory (mutable state)."""
from pathlib import Path

from services.path_config import get_backup_dir

DEFAULT_COMPONENTS = {
    "settings":    True,   # tool config
    "preferences": True,   # user preferences
    "scheduler":   True,   # scheduler
    "watchlist":   True,   # watchlist scan data
    "logs":        False,  # log files
    "pg_dump":     True,   # full PostgreSQL dump
}

RETENTION_DAYS_KEY = "backup.retention_days"
DEFAULT_RETENTION = 30

_runtime_backup_dir: Path | None = None


def get_current_backup_dir() -> Path:
    return _runtime_backup_dir or get_backup_dir()


def set_runtime_backup_dir(path: Path) -> None:
    global _runtime_backup_dir
    _runtime_backup_dir = path
