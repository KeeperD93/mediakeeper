"""Path validation and name sanitisation."""
import os
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
    """Check that a path lives under an allowed media folder without traversal.

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


def _ensure_within_media_roots(path: str) -> Path | None:
    """Return the resolved ``Path`` if it lives under a configured media root, else ``None``.

    Combines anchored ``Path.resolve(strict=False)`` with ``os.path.commonpath``
    containment check. ``os.path.commonpath`` is a recognised barrier guard for
    the CodeQL ``py/path-injection`` query: when a downstream sink uses the
    ``Path`` returned by this helper (instead of the input string), the taint
    flow is broken from the static-analyser standpoint.

    Backup-zone exclusion is enforced as a second guard: even if the path
    resolves under a legitimate media root, paths that fall inside the backup
    directory are refused — media-manager must never be a vector to read or
    mutate backup files.

    **Caller contract** — to actually break the CodeQL taint flow, callers
    MUST use the returned ``Path`` for every downstream filesystem operation
    (``exists``, ``is_dir``, ``samefile``, ``resolve``, ``rename``,
    ``iterdir``, ``unlink``, etc.) rather than reconstructing a new
    ``Path(input_string)``. Passing the input string through this helper but
    then operating on a freshly-built ``Path(input_string)`` defeats the
    purpose.
    """
    try:
        resolved = Path(path).expanduser().resolve(strict=False)
    except (ValueError, OSError, RuntimeError):
        return None
    resolved_str = str(resolved)
    for root in _media_roots():
        root_str = str(root)
        try:
            if os.path.commonpath([root_str, resolved_str]) == root_str:
                if is_path_within_backup_dir(resolved):
                    return None
                return resolved
        except ValueError:
            # Raised on Windows when paths live on different drives — not a match.
            continue
    return None


def _validate_path(path: str) -> str | None:
    """Validate a path. Return an error code or None if valid.

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
    """Sanitise a file/folder name.

    Linear-time rewrite of the previous ``re.sub(r'\\s*:\\s*', ...)`` +
    ``re.sub(r'\\s{2,}', ...)`` combo, which CodeQL flagged as
    polynomial-degree (py/polynomial-redos #143). The ``\\s*X\\s*`` greedy
    pattern is O(n²) on inputs made of unmatched whitespace; ``split``
    + ``join`` is O(n) with the same effective output for well-formed
    inputs. As a side benefit, isolated tabs/newlines in filenames
    (which are anomalous and break shell scripts / display) are now
    normalised to single spaces.
    """
    name = name.replace('/', ' ').replace('\\', ' ').replace(',', '')
    name = re.sub(r'[<>"|?*]', '', name)
    if ':' in name:
        name = ' - '.join(part.strip() for part in name.split(':'))
    return ' '.join(name.split())


def _validate_name(name: str) -> str | None:
    """Validate a file name. Return an error code or None if valid."""
    stripped = name.strip() if name else ""
    if not stripped:
        return "empty_name"
    if '/' in name or '\\' in name:
        return "name_not_allowed"
    # Reject names made only of dots/spaces ('.', '..', '...', '. .'): on Windows
    # the FS strips trailing dots/spaces, so such a name resolves to the parent
    # directory (a merge-into-parent + delete vector). Titles that merely contain
    # an ellipsis keep real text and pass ("Fontaine...mkv".rstrip('. ') is text).
    if not stripped.rstrip('. '):
        return "name_not_allowed"
    return None
