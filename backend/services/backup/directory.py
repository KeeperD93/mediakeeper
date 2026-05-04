"""Backup directory management (listing + runtime change)."""
import logging
import os
from pathlib import Path

from services.path_config import get_existing_path_roots, is_backup_dir_locked, validate_path_in_roots

from ._state import get_current_backup_dir, set_runtime_backup_dir

logger = logging.getLogger("mediakeeper.backup")


def list_available_backup_dirs() -> list[str]:
    """
    List the directories available for storing backups.
    Look up common mounted volumes and check write permissions.
    """
    candidates = set()
    candidates.add(str(get_current_backup_dir()))
    for root in get_existing_path_roots():
        candidates.add(str(root))

    result = []
    for c in sorted(candidates):
        p = Path(c)
        try:
            if p.exists() and p.is_dir() and os.access(str(p), os.W_OK):
                result.append(c)
            elif not p.exists():
                parent = p.parent
                if parent.exists() and os.access(str(parent), os.W_OK):
                    result.append(c)
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass

    return result


def set_backup_directory(new_path: str):
    """Change the backup directory at runtime."""
    if is_backup_dir_locked():
        raise ValueError("BACKUP_PATH locks the backup directory")

    p, path_error = validate_path_in_roots(
        new_path,
        allow_missing=True,
        must_be_dir=True,
        label="Backup directory",
    )
    if path_error == "parent_directory_not_found":
        candidate = Path(new_path).expanduser().resolve(strict=False)
        ancestor = candidate.parent
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        if ancestor.exists():
            if not ancestor.is_dir():
                raise ValueError("parent_not_a_directory")
            if not os.access(str(ancestor), os.W_OK):
                raise ValueError(f"parent_directory_not_writable: {ancestor}")
            p = candidate
            path_error = None
    if path_error:
        if path_error == "path_outside_configured_zones":
            raise ValueError("MEDIAKEEPER_PATH_ROOTS or BACKUP_PATH forbids this path")
        if path_error == "parent_directory_not_found":
            raise ValueError("parent_directory_not_found")
        raise ValueError(path_error)

    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"cannot_create_directory: {e}")

    if not os.access(str(p), os.W_OK):
        raise ValueError(f"directory_not_writable: {new_path}")

    set_runtime_backup_dir(p)
    logger.info(f"[backup] Directory changed to : {p}")
