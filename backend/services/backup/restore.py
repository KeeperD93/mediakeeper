"""Restauration d'un backup ZIP ou d'un JSON unique."""
import json
import logging
import zipfile
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.scheduler_task import SchedulerTask

logger = logging.getLogger("mediakeeper.backup")

ENCRYPTION_KEY_ARCHIVE_NAME = "secrets/.encryption_key"

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
    "archive will only be decryptable by the instance that produced it. "
    "Provide the original key on the target host before starting the "
    "application or expect encrypted values to read back as empty strings."
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
    from services.settings import set_settings_map
    await set_settings_map(db, data, commit=False)
    return "ok"


async def _restore_preferences(db: AsyncSession, data: list) -> str:
    from services.settings import upsert_user_preferences
    for pref in data:
        await upsert_user_preferences(
            db,
            pref["user_id"],
            preferences=json.dumps(pref.get("preferences", {})),
            dashboard_layout=json.dumps(pref["dashboard_layout"]) if pref.get("dashboard_layout") else None,
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
    component = plan[0][0]
    transaction = db.begin_nested() if db.in_transaction() else db.begin()
    try:
        async with transaction:
            for component, payload, handler in plan:
                await handler(db, payload)
                results[component] = "ok"
        return results
    except Exception as exc:
        logger.error("[backup] Restore %s failed: %s", component, exc, exc_info=True)
        results[component] = f"error:{type(exc).__name__}"
        if raise_on_error:
            raise BackupRestoreError(component, exc, results) from exc
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


async def restore_backup(
    db: AsyncSession,
    zip_path: Path,
    components: Optional[dict] = None,
) -> dict:
    """Restaure un backup. Return un dict {component: 'ok'|'error'|'skipped'}."""
    results = {
        "settings": "skipped",
        "preferences": "skipped",
        "scheduler": "skipped",
        "watchlist": "skipped",
    }
    opts = components or {}
    restore_plan: list[tuple[str, object, object]] = []
    encryption_key_info: dict | None = None

    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

            if opts.get("settings") and "settings.json" in names:
                restore_plan.append(
                    (
                        "settings",
                        json.loads(zf.read("settings.json")),
                        _restore_settings,
                    )
                )

            if opts.get("preferences") and "preferences.json" in names:
                restore_plan.append(
                    (
                        "preferences",
                        json.loads(zf.read("preferences.json")),
                        _restore_preferences,
                    )
                )

            if opts.get("scheduler") and "scheduler.json" in names:
                restore_plan.append(
                    (
                        "scheduler",
                        json.loads(zf.read("scheduler.json")),
                        _restore_scheduler,
                    )
                )

            if opts.get("watchlist") and "watchlist.json" in names:
                restore_plan.append(
                    (
                        "watchlist",
                        json.loads(zf.read("watchlist.json")),
                        _restore_watchlist,
                    )
                )

            encryption_key_info = _inspect_encryption_key(zf)
    except zipfile.BadZipFile:
        raise InvalidBackupArchiveError("invalid_or_corrupted_zip") from None

    await _run_restore_plan(db, restore_plan, results, raise_on_error=True)

    if encryption_key_info is not None:
        results["encryption_key"] = encryption_key_info

    logger.info(f"[backup] Restore complete : {results}")
    return results


async def restore_json_backup(
    db: AsyncSession,
    data: dict,
    components: Optional[dict] = None,
) -> dict:
    """
    Restore a single JSON file (settings, preferences, scheduler or watchlist).
    Automatic content-type detection.
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
