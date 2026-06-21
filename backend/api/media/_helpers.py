"""Shared helpers for the media router (navigation roots + validation)."""
from pathlib import Path

from services.media_manager import MEDIA_FOLDERS
from services.path_config import (
    get_existing_media_path_roots,
    is_path_within_backup_dir,
    validate_path_in_roots,
)


def _get_browse_roots() -> list[dict]:
    roots: dict[str, dict] = {}
    # Media-only roots: the backup zone must never be browsable through the
    # media manager, even when it lives inside a media root.
    configured_roots = get_existing_media_path_roots()

    def _add_root(path: Path | None):
        if path is None:
            return
        try:
            resolved = path.resolve()
        except (ValueError, OSError, RuntimeError):
            return
        if not resolved.exists() or not resolved.is_dir():
            return
        if is_path_within_backup_dir(resolved):
            return
        _, error = validate_path_in_roots(
            resolved,
            must_be_dir=True,
            roots=configured_roots,
            label="Browse root",
        )
        if error:
            return
        key = str(resolved)
        roots[key] = {
            "name": resolved.name or key,
            "path": key,
        }

    for root in configured_roots:
        _add_root(root)
    for base in MEDIA_FOLDERS.values():
        _add_root(Path(base) if base else None)

    return sorted(roots.values(), key=lambda item: item["path"].lower())


def _is_allowed_browse_path(target: Path) -> bool:
    try:
        resolved = target.resolve()
    except (ValueError, OSError, RuntimeError):
        return False

    # The backup zone is off-limits even when it sits inside a media root.
    if is_path_within_backup_dir(resolved):
        return False

    for root in _get_browse_roots():
        try:
            root_path = Path(root["path"]).resolve()
        except (ValueError, OSError, RuntimeError):
            continue
        if resolved == root_path or root_path in resolved.parents:
            return True
    return False
