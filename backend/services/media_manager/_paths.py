"""Validation des paths et assainissement des noms."""
import re
from pathlib import Path

from .categories import MEDIA_FOLDERS
from services.path_config import (
    get_configured_path_roots,
    is_path_within_backup_dir,
    validate_path_in_roots,
)

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.wmv'}


def _media_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    def _add(path: str | Path | None) -> None:
        if not path:
            return
        try:
            resolved = Path(path).expanduser().resolve(strict=False)
        except (ValueError, OSError, RuntimeError):
            return
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        roots.append(resolved)

    for base in MEDIA_FOLDERS.values():
        _add(base)
    if not roots:
        for root in get_configured_path_roots():
            _add(root)
    return roots


def _is_allowed_path(path: str) -> bool:
    """Check qu'un path est sous un folder media allowed et without traversal.

    Also rejects anything that resolves into the backup zone, even when the
    backup directory legitimately lives inside a media root: media-manager
    must never be a vector to read or mutate backup files.
    """
    resolved, error = validate_path_in_roots(
        path,
        allow_missing=True,
        roots=_media_roots(),
        label="Media path",
    )
    if error is not None:
        return False
    if resolved is not None and is_path_within_backup_dir(resolved):
        return False
    return True


def _validate_path(path: str) -> str | None:
    """Valide un path. Return un message d'error ou None si valid.

    All ``path_outside_configured_zones`` / ``invalid_path`` /
    ``no_roots_configured`` outcomes — and any path that lands in the backup
    zone — are normalised to the user-facing code ``path_not_allowed`` so
    callers do not leak filesystem details to API responses.
    """
    resolved, error = validate_path_in_roots(
        path,
        allow_missing=True,
        roots=_media_roots(),
        label="Media path",
    )
    if error in {"invalid_path", "path_outside_configured_zones", "no_roots_configured"}:
        return "path_not_allowed"
    if error:
        return error
    if resolved is not None and is_path_within_backup_dir(resolved):
        return "path_not_allowed"
    return None


def _sanitize_name(name: str) -> str:
    """Assainit un nom de file/folder."""
    name = name.replace('/', ' ').replace('\\', ' ')
    name = re.sub(r'\s*:\s*', ' - ', name)
    name = name.replace(',', '')
    name = re.sub(r'[<>"|?*]', '', name)
    name = re.sub(r'\s{2,}', ' ', name)
    return name.strip()


def _validate_name(name: str) -> str | None:
    """Valide un nom de file. Return un message d'error ou None."""
    if not name or not name.strip():
        return "empty_name"
    # Path traversal : seul le segment exact ".." est dangereux comme
    # composant de chemin. Autoriser les "..." dans les titres légitimes
    # (ex. "Fontaine je ne boirai pas...mkv").
    if '/' in name or '\\' in name:
        return "name_not_allowed"
    if name.strip() in ('.', '..'):
        return "name_not_allowed"
    return None
