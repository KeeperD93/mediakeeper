"""
Path configuration helpers driven by docker-compose.

- MEDIAKEEPER_PATH_ROOTS : liste des roots accessibles par l'application
  (separator ',' or ';')
- BACKUP_PATH: backup directory, ideally under one of the roots above
"""

import os
import re
from pathlib import Path
from typing import Iterable

PATH_ROOTS_ENV = "MEDIAKEEPER_PATH_ROOTS"
BACKUP_PATH_ENV = "BACKUP_PATH"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = Path("/data")


def _split_env_paths(raw: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,]", raw or "") if part.strip()]


def _resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def get_configured_path_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    for raw in _split_env_paths(os.getenv(PATH_ROOTS_ENV, "")):
        try:
            resolved = _resolve_path(raw)
        except (OSError, RuntimeError):
            continue

        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        roots.append(resolved)

    return roots


def get_existing_path_roots() -> list[Path]:
    return [root for root in get_configured_path_roots() if root.exists() and root.is_dir()]


def _safe_resolve_backup_dir() -> Path | None:
    """Resolve the backup directory or ``None`` if it cannot be determined.

    ``get_backup_dir`` may raise (production refuses to fall back to a default
    when ``BACKUP_PATH`` is missing). For helpers that only need to *exclude*
    backup zones from media surfaces, that exception is benign — we simply
    cannot enforce the exclusion and return ``None``.
    """
    try:
        return get_backup_dir().resolve(strict=False)
    except (OSError, RuntimeError):
        return None


def is_path_within_backup_dir(path: str | Path) -> bool:
    """Return True if *path* is the backup directory itself or lives inside it.

    Used to make sure media surfaces (categories, file resolution) never expose
    or traverse the backup zone, even when an operator configured both as the
    same or nested filesystem locations.
    """
    backup_dir = _safe_resolve_backup_dir()
    if backup_dir is None:
        return False
    try:
        resolved = _resolve_path(path)
    except (OSError, RuntimeError):
        return False
    return resolved == backup_dir or backup_dir in resolved.parents


def get_existing_media_path_roots() -> list[Path]:
    """Configured roots that are safe to expose as media surfaces.

    A configured root is excluded when it is the backup directory itself or a
    descendant of it. This is intentionally narrower than
    :func:`get_existing_path_roots`: ``set_backup_directory`` legitimately
    needs to validate a candidate backup path against the full root list, so
    we must not break that flow by filtering globally.
    """
    backup_dir = _safe_resolve_backup_dir()
    media_roots: list[Path] = []
    for root in get_existing_path_roots():
        try:
            resolved = root.resolve(strict=False)
        except (OSError, RuntimeError):
            continue
        if backup_dir is not None and (
            resolved == backup_dir or backup_dir in resolved.parents
        ):
            continue
        media_roots.append(resolved)
    return media_roots


def is_path_within_roots(path: str | Path, roots: Iterable[Path] | None = None) -> bool:
    try:
        resolved = _resolve_path(path)
    except (OSError, RuntimeError):
        return False

    actual_roots = list(roots if roots is not None else get_configured_path_roots())
    if not actual_roots:
        return False

    for root in actual_roots:
        if resolved == root or root in resolved.parents:
            return True
    return False


def validate_path_in_roots(
    path: str | Path,
    *,
    allow_missing: bool = False,
    must_be_dir: bool | None = None,
    allowed_suffixes: set[str] | None = None,
    roots: Iterable[Path] | None = None,
    label: str = "Chemin",
) -> tuple[Path | None, str | None]:
    raw = str(path or "").strip()
    if not raw:
        return None, "empty_path"

    try:
        resolved = _resolve_path(raw)
    except (OSError, RuntimeError):
        return None, "invalid_path"

    actual_roots = list(roots if roots is not None else get_configured_path_roots())
    if not actual_roots:
        return None, "no_roots_configured"

    if not is_path_within_roots(resolved, actual_roots):
        return None, "path_outside_configured_zones"

    if allowed_suffixes is not None and resolved.suffix.lower() not in allowed_suffixes:
        return None, "file_type_not_allowed"

    if allow_missing:
        parent = resolved.parent
        if not parent.exists() or not parent.is_dir():
            return None, "parent_directory_not_found"
    elif not resolved.exists():
        return None, "path_not_found"

    if must_be_dir is True and resolved.exists() and not resolved.is_dir():
        return None, "must_be_directory"
    if must_be_dir is False and resolved.exists() and not resolved.is_file():
        return None, "must_be_file"

    return resolved, None


def get_backup_dir() -> Path:
    raw = os.getenv(BACKUP_PATH_ENV, "").strip()
    if raw:
        return _resolve_path(raw)
    if DATA_ROOT.is_dir():
        # Production container detected (DATA_ROOT mounted) but BACKUP_PATH
        # is unset. Refuse to fall back to /data/backups: that would store
        # backups inside the same Docker volume as the PostgreSQL cluster
        # they are meant to protect, defeating their purpose during a volume
        # corruption or cryptolocker incident.
        raise RuntimeError(
            f"{BACKUP_PATH_ENV} is required when running with {DATA_ROOT} "
            "mounted. Configure it through your compose override "
            "(see docker-compose.override.example.yml) so backups land on "
            "a host-managed bind mount, not inside the application volume."
        )
    return (PROJECT_ROOT / "backups").resolve(strict=False)


def is_backup_dir_locked() -> bool:
    return bool(os.getenv(BACKUP_PATH_ENV, "").strip())
