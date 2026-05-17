"""Scheduled task handlers — lazy imports to avoid cycles."""
import json

from sqlalchemy.ext.asyncio import AsyncSession

from ._progress import update_progress


async def _handler_watchlist(db: AsyncSession) -> None:
    from services.watchlist_scanner import full_scan
    await full_scan(db, progress_cb=lambda c, t, label: update_progress("watchlist_scan", c, t, label))


async def _handler_duplicates(db: AsyncSession) -> None:
    from services.emby import get_duplicates
    await get_duplicates(db, progress_cb=lambda c, t, label: update_progress("duplicates_scan", c, t, label))


async def _handler_emby_refresh(db: AsyncSession) -> None:
    from services.emby import refresh_library
    await refresh_library(db)


async def _handler_log_cleanup(db: AsyncSession) -> None:
    from services.logs import fetch_and_store_emby_logs, rotate_logs_if_needed
    rotate_logs_if_needed()
    await fetch_and_store_emby_logs(db)


async def _handler_notifications(db: AsyncSession) -> None:
    from services.notification_engine import check_and_send_notifications
    await check_and_send_notifications()


async def _handler_backup(db: AsyncSession) -> None:
    from services.backup import apply_retention, create_backup
    from services.settings import get_setting

    components_raw = await get_setting(db, "backup.auto_components") or "{}"
    try:
        components = json.loads(components_raw)
    except Exception:
        components = {}
    await create_backup(
        db,
        components=components,
        label="auto",
        progress_cb=lambda c, t, label: update_progress("backup_auto", c, t, label),
    )
    retention = int(await get_setting(db, "backup.retention_days") or 30)
    apply_retention(retention)


async def _handler_healthcheck(db: AsyncSession) -> None:
    from services.healthcheck import run_healthcheck
    await run_healthcheck(db, progress_cb=lambda c, t, label: update_progress("healthcheck_scan", c, t, label))


async def _handler_subtitle_auto(db: AsyncSession) -> None:
    from services.subtitle_auto import check_and_download_new
    await check_and_download_new(db)


async def _handler_expire_users(db: AsyncSession) -> None:
    from services.portal.admin_users_expiration import expire_due_users
    await expire_due_users(db)


async def _handler_gdpr_purge(db: AsyncSession) -> None:
    """Hard-delete users whose GDPR grace period has lapsed.

    Early-returns when ``gdpr.enabled`` is false so the task is safe
    to leave on by default — flipping the toggle is the only way for
    rows to actually be removed.
    """
    from services.portal.gdpr import purge_pending_deletions
    await purge_pending_deletions(db)


async def _handler_clear_image_cache(_db: AsyncSession) -> dict:
    """Wipe the on-disk image proxy cache.

    OFF by default — the admin opts in explicitly via the scheduler
    UI (or clicks "Vider" on the cache row, which calls the same
    helper). Returns the count for the observability surface.
    """
    from services.portal.image_cache import clear_cache
    removed = clear_cache()
    return {"removed": removed}


async def _handler_cleanup_available_requests(db: AsyncSession) -> dict:
    """Drop ``available`` media requests older than the configured window.

    Early-returns when ``requests.auto_cleanup_days`` is 0 (or unset) so
    the task is harmless to leave on by default — flipping the setting
    to a positive value is the only way for rows to actually be removed.
    """
    from services.portal import requests_cleanup
    days = await requests_cleanup.get_cleanup_days(db)
    if days <= 0:
        return {"deleted": 0, "skipped": "disabled"}
    deleted = await requests_cleanup.cleanup_old_available_requests(db, days=days)
    return {"deleted": deleted, "days": days}


