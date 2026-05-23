"""Retention policy for FFmpeg remux rollback artifacts.

The remux flow in :mod:`services.opensubtitles.remove` keeps a sibling rollback
copy named ``.<stem>.rollback-<nonce><suffix>`` next to the source after a
successful destructive operation. These artifacts let an operator recover the
original bytes if a regression is noticed later. Without retention they would
accumulate forever next to the media files.

This helper is intentionally **separate** from the application backup ZIPs in
:mod:`services.backup.listing`: they have different purpose, naming and
locations. Mixing them would risk cross-deletion.
"""
import re
import time
from pathlib import Path
from typing import Iterable

from ._constants import logger

# Strict pattern: dot + stem + .rollback- + 12 hex chars + optional suffix.
# The nonce is produced by ``uuid.uuid4().hex[:12]`` so 12 hex chars is enough
# to avoid colliding with arbitrary user filenames.
_ROLLBACK_NAME_RE = re.compile(
    r"^\.(?P<stem>.+)\.rollback-(?P<nonce>[0-9a-fA-F]{12})(?P<suffix>\.[^.]+)?$"
)

# 30 days — conservative default. Enough time for an operator to roll back a
# regression spotted in normal usage, short enough to avoid filling the disk.
DEFAULT_RETENTION_SECONDS = 30 * 24 * 3600


def is_rollback_artifact(path: Path) -> bool:
    """Return True if *path* matches the strict rollback-artifact naming."""
    return _ROLLBACK_NAME_RE.fullmatch(path.name) is not None


def _resolve_for_compare(path: Path) -> Path | None:
    """Resolve *path* without requiring it to exist; return ``None`` on error.

    Used to compare a candidate rollback against an exclusion set without
    being defeated by ``.``/``..`` segments or by a path written with a
    different but equivalent form.
    """
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError):
        return None


def purge_rollback_artifacts(
    directory: Path,
    *,
    retention_seconds: int = DEFAULT_RETENTION_SECONDS,
    now: float | None = None,
    exclude_paths: Iterable[Path] | None = None,
) -> int:
    """Delete rollback artifacts older than *retention_seconds* in *directory*.

    Strict guarantees:

    - Only files whose name matches the strict ``.<stem>.rollback-<nonce><suffix>``
      pattern are considered. Any other file is left untouched.
    - The original media file (``<stem><suffix>``) is never targeted because it
      does not start with a dot and does not contain ``.rollback-`` after a dot.
    - Any path passed via *exclude_paths* is **never** unlinked, regardless of
      its mtime. This is the contract that lets the caller invoke the purge
      opportunistically right after producing a fresh rollback: even if the
      caller's earlier ``os.utime`` refresh failed (read-only filesystem, FAT,
      restrictive SMB), the freshly-created rollback survives the sweep.
      Comparison is done on resolved paths (``Path.resolve(strict=False)``) so
      callers can pass the same path in any equivalent form.
    - Best-effort: any ``OSError`` while iterating or unlinking is logged at
      debug level. The function never raises, so callers can invoke it
      opportunistically inside a destructive flow without risking to break a
      remux that would otherwise be safe.

    Returns the number of files removed.
    """
    if retention_seconds <= 0:
        return 0
    try:
        if not directory.is_dir():
            return 0
    except OSError as exc:
        logger.debug(f"[opensubtitles] Rollback purge: cannot stat {directory}: {exc}")
        return 0

    excluded: set[Path] = set()
    if exclude_paths:
        for raw in exclude_paths:
            resolved = _resolve_for_compare(Path(raw))
            if resolved is not None:
                excluded.add(resolved)

    cutoff = (now if now is not None else time.time()) - retention_seconds
    removed = 0
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        logger.debug(f"[opensubtitles] Rollback purge: cannot list {directory}: {exc}")
        return 0

    for entry in entries:
        try:
            if not entry.is_file():
                continue
            if not is_rollback_artifact(entry):
                continue
            if excluded:
                resolved = _resolve_for_compare(entry)
                if resolved is not None and resolved in excluded:
                    continue
            mtime = entry.stat().st_mtime
            if mtime >= cutoff:
                continue
            entry.unlink(missing_ok=True)
            removed += 1
            logger.info(f"[opensubtitles] Rollback retention removed {entry.name}")
        except OSError as exc:
            logger.debug(f"[opensubtitles] Rollback purge skipped {entry}: {exc}")
        except Exception as exc:  # noqa: BLE001 -- best-effort, never propagate
            logger.debug(f"[opensubtitles] Rollback purge unexpected error {entry}: {exc}")
    return removed
