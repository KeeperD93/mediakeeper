"""Constants + backup destination directory resolution."""
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from services.path_config import get_backup_dir, is_backup_dir_locked

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


async def resolve_backup_dir(db: AsyncSession) -> Path:
    """Resolve the active backup directory from the DB setting (single source
    of truth), falling back to the env/default when unset.

    No per-process cache: every caller — including the background worker, which
    previously only read this at boot — sees the directory the admin configured.
    """
    from services.settings import get_setting

    # BACKUP_PATH always wins: when the directory is env-locked, ignore any
    # stale DB override (a value persisted before the lock was added) so backups
    # never land somewhere other than the operator-pinned path.
    if is_backup_dir_locked():
        return get_backup_dir()
    saved = await get_setting(db, "backup.directory")
    return Path(saved).expanduser() if saved else get_backup_dir()
