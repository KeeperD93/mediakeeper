"""Restore a backup ZIP or a single JSON."""
import asyncio
import json
import logging
import zipfile
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.scheduler_task import SchedulerTask
from models.settings import Setting
from models.user import User

from ._restore_memory import apply_restored_settings, apply_restored_watchlist
from .restore_secrets import is_unreadable_secret, refuse_unreadable_secrets

logger = logging.getLogger("mediakeeper.backup")

ENCRYPTION_KEY_ARCHIVE_NAME = "secrets/.encryption_key"

# Not the configuration a backup carries: an old announcement date would announce
# already announced media again, an old retention would delete what today's one keeps.
SETTINGS_KEPT_ON_RESTORE = frozenset({
    "backup.directory",
    "backup.retention_days",
    "bug_report.reject_retention_days",
    "chat.retention_days",
    "notifications.last_emby_date",
    "setup.onboarding_done",
    "subtitle_auto.last_check",
})

# Restore never writes the Fernet key automatically: an operator must extract
# it consciously and place it where the next process will pick it up. The
# string below is surfaced through the restore result so the UI/CLI can
# display the recovery procedure without parsing the manifest itself.
_ENCRYPTION_KEY_MANUAL_HINT = (
    "Encryption key found in backup. Manual recovery required: extract "
    f"'{ENCRYPTION_KEY_ARCHIVE_NAME}' from the ZIP and either set "
    "MEDIAKEEPER_ENCRYPTION_KEY or write the value to /data/.encryption_key "
    "before starting the application. The key is intentionally not restored "
    "automatically to keep secret rotation under operator control."
)
_ENCRYPTION_KEY_MISSING_HINT = (
    "No encryption key found in this backup. Encrypted settings inside the "
    "archive will only be decryptable by the instance that produced it: "
    "without its key on the target host, they are not restored."
)


class InvalidBackupArchiveError(Exception):
    """Raised when the provided archive is not a valid ZIP backup."""


class BackupRestoreError(Exception):
    """Raised when a restore plan fails and is rolled back."""

    def __init__(self, component: str, reason: Exception, results: dict):
        self.component = component
        self.reason = reason
        self.results = dict(results)
        super().__init__(f"{component}: {reason}")


async def _restore_settings(db: AsyncSession, data: dict) -> str:
    from services.portal.gdpr import (
        get_purge_delay_days,
        is_gdpr_enabled,
        refresh_pending_grace,
    )
    from services.settings import set_settings_map

    gdpr_was_off = not await is_gdpr_enabled(db)
    restored = {
        k: v for k, v in data.items() if k not in SETTINGS_KEPT_ON_RESTORE and not is_unreadable_secret(v)
    }
    await set_settings_map(db, restored, commit=False)
    # As on the GDPR screen: a deletion frozen while GDPR was off gets a fresh delay.
    if gdpr_was_off and await is_gdpr_enabled(db):
        await refresh_pending_grace(db, delay_days=await get_purge_delay_days(db), commit=False)
    return "ok"


async def _replace_settings(db: AsyncSession, data: dict) -> str:
    """A ZIP holds the whole configuration of its moment: a setting it lacks was still
    at its default, so it goes back there. An empty file says nothing and removes nothing."""
    await _restore_settings(db, data)
    if data:
        await db.execute(
            delete(Setting)
            .where(Setting.key.not_in([*data, *SETTINGS_KEPT_ON_RESTORE]))
            .execution_options(synchronize_session="fetch")
        )
    return "ok"


async def _restore_preferences(db: AsyncSession, data: list) -> str:
    from services.settings import upsert_user_preferences

    user_ids = list({pref["user_id"] for pref in data})
    known = set((await db.execute(select(User.id).where(User.id.in_(user_ids)))).scalars())
    # An account deleted since the backup has nothing left to restore to.
    if len(known) < len(user_ids):
        logger.info("[backup] Preferences of %d deleted account(s) skipped", len(user_ids) - len(known))
    for pref in data:
        if pref["user_id"] not in known:
            continue
        await upsert_user_preferences(
            db,
            pref["user_id"],
            preferences=json.dumps(pref.get("preferences", {})),
            dashboard_layout=json.dumps(pref["dashboard_layout"]) if pref.get("dashboard_layout") else None,
            table_columns=json.dumps(pref["table_columns"]) if pref.get("table_columns") else None,
            commit=False,
        )
    return "ok"


async def _restore_scheduler(db: AsyncSession, data: list) -> str:
    for task_data in data:
        result = await db.execute(
            select(SchedulerTask).where(SchedulerTask.key == task_data["key"])
        )
        row = result.scalar_one_or_none()
        if row:
            row.enabled = task_data.get("enabled", row.enabled)
            row.interval_sec = task_data.get("interval_sec", row.interval_sec)
    await db.flush()
    return "ok"


async def _restore_watchlist(db: AsyncSession, data: list) -> str:
    from services.settings import set_watchlist_data
    for scan in data:
        await set_watchlist_data(db, scan["scan_key"], scan["data"], commit=False)
    return "ok"


async def _run_restore_plan(
    db: AsyncSession,
    plan: list[tuple[str, object, object]],
    results: dict,
    *,
    raise_on_error: bool = True,
) -> dict:
    if not plan:
        return results
    refuse_unreadable_secrets(plan)
    component = plan[0][0]
    try:
        async with db.begin_nested():
            for component, payload, handler in plan:
                await handler(db, payload)
                results[component] = "ok"
        # The routes have already read through this session: only a commit saves the savepoint.
        await db.commit()
    except Exception as exc:
        logger.exception("[backup] Restore %s failed: %s", component, exc)
        results[component] = f"error:{type(exc).__name__}"
        if raise_on_error:
            raise BackupRestoreError(component, exc, results) from exc
        return results
    parts = {part for part, _, _ in plan}
    if "settings" in parts:
        await apply_restored_settings(db)
    if "watchlist" in parts:
        await apply_restored_watchlist(db)
    return results


def _inspect_encryption_key(zf: zipfile.ZipFile) -> dict:
    """Read the manifest's encryption-key block + verify the archive entry.

    Never extracts or writes the key — only reports what is available so an
    operator can perform the recovery manually. The status returned drives
    the hint surfaced in the restore results.
    """
    manifest: dict = {}
    if "manifest.json" in zf.namelist():
        try:
            manifest = json.loads(zf.read("manifest.json"))
        except Exception:
            manifest = {}

    block = manifest.get("encryption_key") if isinstance(manifest, dict) else None
    archive_has_key = ENCRYPTION_KEY_ARCHIVE_NAME in zf.namelist()
    declared_status = (block or {}).get("status") if isinstance(block, dict) else None

    if archive_has_key:
        return {
            "status": "present",
            "source": (block or {}).get("source") if isinstance(block, dict) else None,
            "archive_path": ENCRYPTION_KEY_ARCHIVE_NAME,
            "hint": _ENCRYPTION_KEY_MANUAL_HINT,
        }

    return {
        "status": declared_status or "absent",
        "source": None,
        "archive_path": None,
        "hint": _ENCRYPTION_KEY_MISSING_HINT,
    }


def _read_restore_plan(zip_path: Path, opts: dict) -> tuple[list[tuple[str, object, object]], dict]:
    """The selected parts the archive holds (``<part>.json``), read and parsed,
    with their handler, and the archive's key status."""
    handlers = {
        "settings": _replace_settings,
        "preferences": _restore_preferences,
        "scheduler": _restore_scheduler,
        "watchlist": _restore_watchlist,
    }
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            plan = [
                (part, json.loads(zf.read(f"{part}.json")), handler)
                for part, handler in handlers.items()
                if opts.get(part) and f"{part}.json" in names
            ]
            return plan, _inspect_encryption_key(zf)
    except zipfile.BadZipFile:
        raise InvalidBackupArchiveError("invalid_or_corrupted_zip") from None


async def restore_backup(
    db: AsyncSession,
    zip_path: Path,
    components: dict | None = None,
) -> dict:
    """Restore a backup. Return a dict {component: 'ok'|'error'|'skipped'}.
    Does NOT restore PostgreSQL relational data; run `psql -f pg_dump.sql`
    first — see docs/operations/backup-restore.md.
    """
    results = {
        "settings": "skipped",
        "preferences": "skipped",
        "scheduler": "skipped",
        "watchlist": "skipped",
    }
    # Reading the archive is file work: off the event loop.
    restore_plan, encryption_key_info = await asyncio.to_thread(
        _read_restore_plan, zip_path, components or {},
    )

    await _run_restore_plan(db, restore_plan, results, raise_on_error=True)

    results["encryption_key"] = encryption_key_info

    logger.info("[backup] Restore complete: %s", results)
    return results


async def restore_json_backup(
    db: AsyncSession,
    data: dict,
    components: dict | None = None,
) -> dict:
    """
    Restore a single JSON file (settings, preferences, scheduler or watchlist).
    Automatic content-type detection. Does NOT touch PostgreSQL data
    (no pg_dump.sql in single-file payloads).
    """
    results = {}
    opts = components or {}
    restore_plan: list[tuple[str, object, object]] = []

    if isinstance(data, dict) and "version" in data and "components" in data:
        results["manifest"] = "skipped (use ZIP for full restore)"
        return results

    if isinstance(data, list) and data and "user_id" in data[0]:
        if opts.get("preferences", True):
            results["preferences"] = "skipped"
            restore_plan.append(("preferences", data, _restore_preferences))
            return await _run_restore_plan(db, restore_plan, results, raise_on_error=False)
        return results

    if isinstance(data, list) and data and "key" in data[0] and "interval_sec" in data[0]:
        if opts.get("scheduler", True):
            results["scheduler"] = "skipped"
            restore_plan.append(("scheduler", data, _restore_scheduler))
            return await _run_restore_plan(db, restore_plan, results, raise_on_error=False)
        return results

    if isinstance(data, list) and data and "scan_key" in data[0]:
        if opts.get("watchlist", True):
            results["watchlist"] = "skipped"
            restore_plan.append(("watchlist", data, _restore_watchlist))
            return await _run_restore_plan(db, restore_plan, results, raise_on_error=False)
        return results

    if isinstance(data, dict) and opts.get("settings", True):
        results["settings"] = "skipped"
        restore_plan.append(("settings", data, _restore_settings))
        return await _run_restore_plan(db, restore_plan, results, raise_on_error=False)

    return results
