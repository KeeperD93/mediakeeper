"""Build a backup ZIP (settings, preferences, scheduler, watchlist, logs, pg_dump)."""
import asyncio
import json
import logging
import os
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.backup import BACKUP_LABEL_MAX_LENGTH
from core.encryption import get_persistent_fernet_key
from models.scheduler_task import SchedulerTask
from models.user_preferences import UserPreference
from services.logs import LOG_DIR
from services.settings import get_all_settings

from ._state import DEFAULT_COMPONENTS, resolve_backup_dir
from .pg_dump import dump_database

logger = logging.getLogger("mediakeeper.backup")

ENCRYPTION_KEY_ARCHIVE_NAME = "secrets/.encryption_key"
# Optional and never restored: a backup missing only its log files still counts
# as complete, so it cannot hold retention up.
OPTIONAL_PARTS = frozenset({"logs"})
# A temporary archive older than any write can take was left by a write cut
# short (crash, restart); a younger one may belong to a backup still running.
STALE_TEMP_AGE_S = 24 * 60 * 60

_INCLUDED_KEY_WARNING = (
    "This archive embeds the active Fernet key under "
    f"'{ENCRYPTION_KEY_ARCHIVE_NAME}'. Anyone with this ZIP can decrypt "
    "every encrypted setting (API keys, webhooks, passwords). Store it "
    "encrypted at rest and treat it as a secret."
)
_EPHEMERAL_KEY_WARNING = (
    "No persistent Fernet key was available when this backup was created "
    "(MEDIAKEEPER_ENCRYPTION_KEY unset and no readable /data/.encryption_key). "
    "Encrypted settings inside this archive will only be decryptable by the "
    "instance that produced it; restoring on another host without first "
    "providing the original key will leave secrets unreadable."
)


@dataclass(frozen=True)
class BackupResult:
    """The archive written, and the requested parts it lacks because their export failed."""

    path: Path
    failed: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """Only optional parts (the log files) may be missing: retention can run."""
        return not set(self.failed) - OPTIONAL_PARTS


def _to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


async def _settings_json(db: AsyncSession) -> str:
    return _to_json(await get_all_settings(db, decrypt_sensitive=False))


async def _preferences_json(db: AsyncSession) -> str:
    prefs = (await db.execute(select(UserPreference))).scalars().all()
    return _to_json([
        {
            "user_id":          p.user_id,
            "preferences":      json.loads(p.preferences) if p.preferences else {},
            "dashboard_layout": json.loads(p.dashboard_layout) if p.dashboard_layout else None,
            "table_columns":    json.loads(p.table_columns) if p.table_columns else None,
        }
        for p in prefs
    ])


async def _scheduler_json(db: AsyncSession) -> str:
    tasks = (await db.execute(select(SchedulerTask))).scalars().all()
    return _to_json([
        {
            "key":          t.key,
            "label":        t.label,
            "enabled":      t.enabled,
            "interval_sec": t.interval_sec,
            "run_count":    t.run_count,
            "last_run":     t.last_run.isoformat() if t.last_run else None,
            "last_status":  t.last_status,
        }
        for t in tasks
    ])


async def _watchlist_json(db: AsyncSession) -> str:
    from models.watchlist_scans import WatchlistScan
    scans = (await db.execute(select(WatchlistScan))).scalars().all()
    return _to_json([{"scan_key": s.scan_key, "data": s.data} for s in scans])


# The database parts: component, archive entry, progress label, exporter.
_DB_EXPORTS = (
    ("settings", "settings.json", "Settings", _settings_json),
    ("preferences", "preferences.json", "Preferences", _preferences_json),
    ("scheduler", "scheduler.json", "Scheduler", _scheduler_json),
    ("watchlist", "watchlist.json", "Watchlist", _watchlist_json),
)


async def create_backup(
    db: AsyncSession,
    components: dict | None = None,
    label: str = "",
    progress_cb=None,
) -> BackupResult:
    """Create a backup ZIP file; a part whose export fails is left out and reported.

    The parts are gathered on the event loop (database, pg_dump); the archive is
    compressed and written in a worker thread. Temporary files left by an
    earlier write cut short are removed first.
    """
    opts = {**DEFAULT_COMPONENTS, **(components or {})}
    backup_dir = await resolve_backup_dir(db)
    await asyncio.to_thread(backup_dir.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(_remove_stale_temp_archives, backup_dir)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Only what the listing's file name check accepts (ASCII letters, digits,
    # - and _): any other name lists fine but cannot be downloaded, deleted
    # or restored.
    kept = "".join(c for c in label if (c.isascii() and c.isalnum()) or c in "-_")
    safe_label = kept[:BACKUP_LABEL_MAX_LENGTH]
    suffix = f"_{safe_label}" if safe_label else ""
    dest = backup_dir / f"mediakeeper_backup_{ts}{suffix}.zip"

    # One step per part gathered here, plus the archive (log files included).
    total_steps = sum(1 for c in DEFAULT_COMPONENTS if c != "logs" and opts.get(c)) + 1
    step = 0
    entries: list[tuple[str, str | bytes]] = []
    failed: list[str] = []

    def next_step(step_label: str) -> None:
        nonlocal step
        step += 1
        if progress_cb:
            progress_cb(step, total_steps, step_label)

    for part, entry, step_label, export in _DB_EXPORTS:
        if not opts.get(part):
            continue
        next_step(step_label)
        try:
            entries.append((entry, await export(db)))
        except Exception as e:
            logger.error("[backup] %s: %r", part, e)
            failed.append(part)

    if opts.get("pg_dump"):
        next_step("Database")
        try:
            sql = await dump_database()
            if not sql:  # dump_database logged why
                raise RuntimeError("no SQL produced")
            entries.append(("pg_dump.sql", sql))
        except Exception as e:
            logger.error("[backup] pg_dump: %r", e)  # %r: a timeout carries no message
            failed.append("pg_dump")

    next_step("Archive")
    failed, size = await asyncio.to_thread(_write_archive, dest, entries, opts, label, failed)
    logger.info("[backup] Created: %s (%s KB)", dest.name, size // 1024)
    if failed:
        logger.warning("[backup] %s written without: %s", dest.name, ", ".join(failed))
    return BackupResult(dest, tuple(failed))


def _write_archive(
    dest: Path,
    entries: list[tuple[str, str | bytes]],
    opts: dict,
    label: str,
    failed: list[str],
) -> tuple[list[str], int]:
    """Compress the parts into ``dest`` (worker thread), with the log files and
    the manifest. Written under a ``.part`` name of its own (two backups started
    in the same second share ``dest``), then moved in place: a write cut short
    (full disk) never leaves a truncated archive under a backup name.
    Returns the parts missing from the archive and its size."""
    failed = list(failed)
    tmp = dest.with_name(f"{dest.name}.{uuid4().hex}.part")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in entries:
                zf.writestr(name, data)
            if opts.get("logs"):
                try:
                    for log_file in LOG_DIR.glob("*.txt"):
                        zf.write(log_file, f"logs/{log_file.name}")
                except Exception as e:
                    logger.error("[backup] logs: %r", e)
                    failed.append("logs")
            manifest = {
                "version":    "1.1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "label":      label,
                # What the archive holds: a requested part whose export failed
                # is false here and named under "failed".
                "components": {c: bool(opts.get(c)) and c not in failed for c in DEFAULT_COMPONENTS},
                "failed":     failed,
                "filename":   dest.name,
                "encryption_key": _embed_encryption_key(zf),
            }
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return failed, dest.stat().st_size


def _remove_stale_temp_archives(backup_dir: Path) -> None:
    """Delete the temporary archives of writes cut short (worker thread). A file
    that cannot go is logged and left for the next backup."""
    cutoff = time.time() - STALE_TEMP_AGE_S
    for tmp in backup_dir.glob("mediakeeper_backup_*.zip.*.part"):
        try:
            if tmp.stat().st_mtime >= cutoff:
                continue
            tmp.unlink()
        except FileNotFoundError:
            continue  # removed meanwhile by another backup
        except OSError as e:
            logger.warning("[backup] Could not remove %s: %r", tmp.name, e)
            continue
        logger.info("[backup] Removed the leftover %s", tmp.name)


def _embed_encryption_key(zf: zipfile.ZipFile) -> dict:
    """Embed the active persistent Fernet key in the archive.

    Returns the metadata block to write into the manifest. When no
    persistent key is available the archive intentionally ships without
    the secret and the manifest carries an explicit warning so an operator
    cannot mistake a partial backup for a full one.
    """
    persistent = get_persistent_fernet_key()
    if persistent is None:
        logger.warning(
            "[backup] No persistent Fernet key found — backup will ship "
            "without %s. Encrypted settings will be unreadable on a fresh "
            "host until the original key is restored manually.",
            ENCRYPTION_KEY_ARCHIVE_NAME,
        )
        return {
            "status": "absent",
            "source": None,
            "archive_path": None,
            "warning": _EPHEMERAL_KEY_WARNING,
        }

    zf.writestr(ENCRYPTION_KEY_ARCHIVE_NAME, persistent.key)
    logger.info(
        "[backup] Persistent Fernet key embedded (source=%s) at %s",
        persistent.source,
        ENCRYPTION_KEY_ARCHIVE_NAME,
    )
    return {
        "status": "included",
        "source": persistent.source,
        "archive_path": ENCRYPTION_KEY_ARCHIVE_NAME,
        "warning": _INCLUDED_KEY_WARNING,
    }
