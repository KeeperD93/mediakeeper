"""Shared helpers for the media router (navigation roots + validation)."""
from pathlib import Path

from services.media_manager import MEDIA_FOLDERS
from services.path_config import get_existing_path_roots, validate_path_in_roots


def _get_browse_roots() -> list[dict]:
    roots: dict[str, dict] = {}
    configured_roots = get_existing_path_roots()

    def _add_root(path: Path | None):
        if path is None:
            return
        try:
            resolved = path.resolve()
        except (ValueError, OSError, RuntimeError):
            return
        if not resolved.exists() or not resolved.is_dir():
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

    for root in _get_browse_roots():
        root_path = Path(root["path"]).resolve()
        if resolved == root_path or root_path in resolved.parents:
            return True
    return False
