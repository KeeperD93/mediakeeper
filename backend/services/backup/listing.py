"""List, manifest reading, deletion and retention of backups."""
import asyncio
import json
import logging
import os
import re
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from ._state import get_retention_days, resolve_backup_dir

logger = logging.getLogger("mediakeeper.backup")

# The label part allows BACKUP_LABEL_MAX_LENGTH characters (constants/backup.py).
_BACKUP_FILENAME_RE = re.compile(
    r"^mediakeeper_backup_\d{8}_\d{6}(?:_[A-Za-z0-9_-]{1,40})?\.zip$"
)

# Listing, deletion and retention run in worker threads (asyncio.to_thread):
# one lock keeps them from tripping over a file another one just removed.
_FILES_LOCK = threading.Lock()


def _mtime(f: Path) -> float | None:
    try:
        return f.stat().st_mtime
    except FileNotFoundError:  # removed meanwhile by the other process (web / worker)
        return None


def _read_manifest(zip_path: Path) -> dict:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            if "manifest.json" in zf.namelist():
                return json.loads(zf.read("manifest.json"))
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass
    return {}


def list_backups(backup_dir: Path) -> list[dict]:
    """Return the list of backups sorted from newest to oldest."""
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        logger.warning("[backup] Directory unreachable for backup listing: %s (%s)", backup_dir, e)
        return []
    backups = []
    with _FILES_LOCK:
        for f in sorted(backup_dir.glob("mediakeeper_backup_*.zip"), reverse=True):
            try:
                stat = f.stat()
            except FileNotFoundError:  # removed meanwhile by the other process (web / worker)
                continue
            manifest = _read_manifest(f)
            backups.append({
                "filename":   f.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "label":      manifest.get("label", ""),
                "components": manifest.get("components", {}),
            })
    return backups


def get_backup_path(filename: str, backup_dir: Path) -> Path | None:
    """Return the full path of a backup if the file exists."""
    if not _BACKUP_FILENAME_RE.fullmatch(filename or ""):
        return None
    # Containment guard in the form CodeQL recognises for py/path-injection:
    # os.path.realpath normalisation + a startswith check on the resolved path
    # (see the query help). The filename allowlist above already blocks
    # traversal; downstream sinks must consume the returned Path.
    base = os.path.realpath(backup_dir)
    resolved = os.path.realpath(os.path.join(base, filename))
    if not resolved.startswith(base + os.sep):
        return None
    path = Path(resolved)
    return path if path.is_file() and path.suffix == ".zip" else None


def delete_backup(filename: str, backup_dir: Path) -> bool:
    with _FILES_LOCK:
        path = get_backup_path(filename, backup_dir)
        if not path:
            return False
        path.unlink(missing_ok=True)
        return True


def apply_retention(retention_days: int, backup_dir: Path) -> int:
    """Delete backups older than retention_days. Returns the number removed."""
    if retention_days <= 0:
        return 0
    # Plain timestamps: an absurd number of days cannot overflow a date.
    cutoff = time.time() - retention_days * 86400
    removed = 0
    with _FILES_LOCK:
        for f in backup_dir.glob("mediakeeper_backup_*.zip"):
            mtime = _mtime(f)
            if mtime is None or mtime >= cutoff:
                continue
            f.unlink(missing_ok=True)
            removed += 1
            logger.info("[backup] Retention: removed %s", f.name)
    return removed


def apply_retention_by_count(max_count: int, backup_dir: Path) -> int:
    """Keep only the N most recent backups. Returns the number removed."""
    if max_count <= 0:
        return 0
    removed = 0
    with _FILES_LOCK:
        dated = [(m, f) for f in backup_dir.glob("mediakeeper_backup_*.zip") if (m := _mtime(f)) is not None]
        dated.sort(key=lambda pair: pair[0], reverse=True)
        for _, f in dated[max_count:]:
            f.unlink(missing_ok=True)
            removed += 1
            logger.info("[backup] Count retention: removed %s", f.name)
    return removed


def apply_retention_for_setting(retention: int, backup_dir: Path) -> int:
    """Apply the ``backup.retention_days`` policy. A negative value means "keep
    the N most recent" (count-based); a positive value means "delete older
    than N days"."""
    if retention < 0:
        return apply_retention_by_count(abs(retention), backup_dir)
    return apply_retention(retention, backup_dir)


async def apply_configured_retention(db: AsyncSession) -> int:
    """Apply the configured policy to the backup directory, off the event loop
    (globbing and deleting archives can stall on a slow NAS). Every caller
    (manual backup, "apply now", scheduled backup) goes through here so the
    paths can't diverge. Returns the number of backups removed."""
    retention = await get_retention_days(db)
    backup_dir = await resolve_backup_dir(db)
    return await asyncio.to_thread(apply_retention_for_setting, retention, backup_dir)
