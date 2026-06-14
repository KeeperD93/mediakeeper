"""Build a backup ZIP (settings, preferences, scheduler, watchlist, logs, pg_dump)."""
import asyncio
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import DATABASE_URL
from core.encryption import get_persistent_fernet_key
from models.scheduler_task import SchedulerTask
from models.user_preferences import UserPreference
from services.logs import LOG_DIR
from services.settings import get_all_settings

from ._state import DEFAULT_COMPONENTS, resolve_backup_dir

logger = logging.getLogger("mediakeeper.backup")

ENCRYPTION_KEY_ARCHIVE_NAME = "secrets/.encryption_key"

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


async def create_backup(
    db: AsyncSession,
    components: dict | None = None,
    label: str = "",
    progress_cb=None,
) -> Path:
    """Create a backup ZIP file. Returns the path of the created file."""
    opts = {**DEFAULT_COMPONENTS, **(components or {})}
    backup_dir = await resolve_backup_dir(db)
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"mediakeeper_backup_{ts}.zip"
    if label:
        safe_label = "".join(c for c in label if c.isalnum() or c in "-_")[:40]
        filename = f"mediakeeper_backup_{ts}_{safe_label}.zip"
    dest = backup_dir / filename

    comp_names = ["settings", "preferences", "scheduler", "watchlist", "logs", "pg_dump"]
    enabled_comps = [c for c in comp_names if opts.get(c)]
    total_steps = len(enabled_comps) + 1  # +1 for the manifest
    step = 0

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        if opts.get("settings"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Settings")
            try:
                all_settings = await get_all_settings(db, decrypt_sensitive=False)
                zf.writestr("settings.json", json.dumps(all_settings, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.error("[backup] settings: %s", e)

        if opts.get("preferences"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Preferences")
            try:
                result = await db.execute(select(UserPreference))
                prefs = result.scalars().all()
                prefs_data = [
                    {
                        "user_id":          p.user_id,
                        "preferences":      json.loads(p.preferences) if p.preferences else {},
                        "dashboard_layout": json.loads(p.dashboard_layout) if p.dashboard_layout else None,
                        "table_columns":    json.loads(p.table_columns) if p.table_columns else None,
                    }
                    for p in prefs
                ]
                zf.writestr("preferences.json", json.dumps(prefs_data, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.error("[backup] preferences: %s", e)

        if opts.get("scheduler"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Scheduler")
            try:
                result = await db.execute(select(SchedulerTask))
                tasks = result.scalars().all()
                tasks_data = [
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
                ]
                zf.writestr("scheduler.json", json.dumps(tasks_data, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.error("[backup] scheduler: %s", e)

        if opts.get("watchlist"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Watchlist")
            try:
                from models.watchlist_scans import WatchlistScan
                result = await db.execute(select(WatchlistScan))
                scans = result.scalars().all()
                scans_data = [{"scan_key": s.scan_key, "data": s.data} for s in scans]
                zf.writestr("watchlist.json", json.dumps(scans_data, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.error("[backup] watchlist: %s", e)

        if opts.get("logs"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Logs")
            try:
                for log_file in LOG_DIR.glob("*.txt"):
                    zf.write(log_file, f"logs/{log_file.name}")
            except Exception as e:
                logger.error("[backup] logs: %s", e)

        if opts.get("pg_dump"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Database")
            try:
                sql = await _pg_dump_async()
                if sql:
                    zf.writestr("pg_dump.sql", sql)
            except Exception as e:
                logger.error("[backup] pg_dump: %s", e)

        encryption_key_meta = _embed_encryption_key(zf)

        manifest = {
            "version":    "1.1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label":      label,
            "components": opts,
            "filename":   filename,
            "encryption_key": encryption_key_meta,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    dest.write_bytes(buf.getvalue())
    size_kb = dest.stat().st_size // 1024
    logger.info("[backup] Created: %s (%s KB)", dest.name, size_kb)
    return dest


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


def _parse_pg_dsn(database_url: str) -> dict[str, str]:
    """Split a SQLAlchemy/asyncpg DSN into pg_dump connection parts.

    urlparse does not percent-decode credentials; the DSN percent-encodes
    reserved chars (@ : / %). Decode them so pg_dump connects with the same
    values asyncpg uses — else auth fails and the archive silently omits the dump.
    """
    parsed = urlparse(database_url.replace("+asyncpg", ""))
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or "mediakeeper"),
        "password": unquote(parsed.password or ""),
        "dbname": unquote((parsed.path or "/mediakeeper_db").lstrip("/")),
    }


async def _pg_dump_async() -> str | None:
    """Start pg_dump in a subprocess and return the SQL."""
    dsn = _parse_pg_dsn(DATABASE_URL)

    env = os.environ.copy()
    env["PGPASSWORD"] = dsn["password"]

    cmd = [
        "pg_dump",
        "-h", dsn["host"],
        "-p", dsn["port"],
        "-U", dsn["user"],
        "-d", dsn["dbname"],
        "--no-owner", "--no-acl", "--if-exists", "--clean",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

    if proc.returncode != 0:
        logger.error("[backup] pg_dump failed: %s", stderr.decode()[:300])
        try:
            from services.monitoring import AlertType, send_alert

            await send_alert(
                AlertType.BACKUP_FAILED,
                {"component": "pg_dump", "returncode": proc.returncode},
            )
        except Exception:
            logger.exception("[backup] Failed to push monitoring alert")
        return None
    return stdout.decode()
