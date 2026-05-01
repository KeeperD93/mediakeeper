"""Build a backup ZIP (settings, preferences, scheduler, watchlist, logs, pg_dump)."""
import asyncio
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import DATABASE_URL
from models.scheduler_task import SchedulerTask
from models.user_preferences import UserPreference
from services.logs import LOG_DIR
from services.settings import get_all_settings

from ._state import DEFAULT_COMPONENTS, get_current_backup_dir

logger = logging.getLogger("mediakeeper.backup")


async def create_backup(
    db: AsyncSession,
    components: Optional[dict] = None,
    label: str = "",
    progress_cb=None,
) -> Path:
    """Create a backup ZIP file. Returns the path of the created file."""
    opts = {**DEFAULT_COMPONENTS, **(components or {})}
    backup_dir = get_current_backup_dir()
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
                logger.error(f"[backup] settings: {e}")

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
                    }
                    for p in prefs
                ]
                zf.writestr("preferences.json", json.dumps(prefs_data, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.error(f"[backup] preferences: {e}")

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
                logger.error(f"[backup] scheduler: {e}")

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
                logger.error(f"[backup] watchlist: {e}")

        if opts.get("logs"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Logs")
            try:
                for log_file in LOG_DIR.glob("*.txt"):
                    zf.write(log_file, f"logs/{log_file.name}")
            except Exception as e:
                logger.error(f"[backup] logs: {e}")

        if opts.get("pg_dump"):
            step += 1
            if progress_cb:
                progress_cb(step, total_steps, "Database")
            try:
                sql = await _pg_dump_async()
                if sql:
                    zf.writestr("pg_dump.sql", sql)
            except Exception as e:
                logger.error(f"[backup] pg_dump: {e}")

        manifest = {
            "version":    "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label":      label,
            "components": opts,
            "filename":   filename,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    dest.write_bytes(buf.getvalue())
    size_kb = dest.stat().st_size // 1024
    logger.info(f"[backup] Created : {dest.name} ({size_kb} KB)")
    return dest


async def _pg_dump_async() -> Optional[str]:
    """Start pg_dump in a subprocess and return the SQL."""
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL.replace("+asyncpg", ""))

    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""

    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "127.0.0.1",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "mediakeeper",
        "-d", (parsed.path or "/mediakeeper_db").lstrip("/"),
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
        logger.error(f"[backup] pg_dump failed: {stderr.decode()[:300]}")
        return None
    return stdout.decode()
