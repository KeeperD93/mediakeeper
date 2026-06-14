"""List, manifest reading, deletion and retention of backups."""
import json
import logging
import os
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("mediakeeper.backup")

_BACKUP_FILENAME_RE = re.compile(
    r"^mediakeeper_backup_\d{8}_\d{6}(?:_[A-Za-z0-9_-]{1,40})?\.zip$"
)


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
    for f in sorted(backup_dir.glob("mediakeeper_backup_*.zip"), reverse=True):
        stat = f.stat()
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
    backup_dir = backup_dir.resolve(strict=False)
    path = (backup_dir / filename).resolve(strict=False)
    # Containment barrier: the resolved target must stay within backup_dir.
    # os.path.commonpath is the form CodeQL recognises as a py/path-injection
    # guard (mirrors services/media_manager/_paths.py); callers must use the
    # returned Path downstream for the taint flow to stay broken.
    backup_dir_str = str(backup_dir)
    try:
        within = os.path.commonpath([backup_dir_str, str(path)]) == backup_dir_str
    except ValueError:  # different drives on Windows
        within = False
    if not within or path.parent != backup_dir:
        return None
    return path if path.exists() and path.is_file() and path.suffix == ".zip" else None


def delete_backup(filename: str, backup_dir: Path) -> bool:
    path = get_backup_path(filename, backup_dir)
    if path:
        path.unlink()
        return True
    return False


def apply_retention(retention_days: int, backup_dir: Path) -> int:
    """Delete backups older than retention_days. Returns the number removed."""
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for f in backup_dir.glob("mediakeeper_backup_*.zip"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            f.unlink()
            removed += 1
            logger.info("[backup] Retention: removed %s", f.name)
    return removed


def apply_retention_by_count(max_count: int, backup_dir: Path) -> int:
    """Keep only the N most recent backups. Returns the number removed."""
    if max_count <= 0:
        return 0
    files = sorted(backup_dir.glob("mediakeeper_backup_*.zip"), key=lambda f: f.stat().st_mtime, reverse=True)
    removed = 0
    for f in files[max_count:]:
        f.unlink()
        removed += 1
        logger.info("[backup] Count retention: removed %s", f.name)
    return removed
