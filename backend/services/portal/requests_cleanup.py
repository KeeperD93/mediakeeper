"""Hygiene job: drop ``available`` media requests older than N days.

Gated by the ``requests.auto_cleanup_days`` setting (0 = disabled).
The scheduler invokes :func:`cleanup_old_available_requests` once per
day.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.request import MediaRequest
from services.settings import get_setting

logger = logging.getLogger("mediakeeper.portal.requests_cleanup")

REQUESTS_AUTO_CLEANUP_KEY = "requests.auto_cleanup_days"


async def get_cleanup_days(db: AsyncSession) -> int:
    """Read the configured retention window. 0 (or invalid) = disabled."""
    raw = await get_setting(db, REQUESTS_AUTO_CLEANUP_KEY)
    if not raw:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def cleanup_old_available_requests(
    db: AsyncSession, *, days: int
) -> int:
    """Delete ``available`` requests with ``available_at`` older than ``days``.

    Returns the number of rows removed. When ``days <= 0`` the function
    is a no-op (disabled) — no query is issued. Rows whose
    ``available_at`` is NULL (legacy, pre-backfill, or never stamped)
    are explicitly skipped so the cleanup can never act on rows whose
    age is unknown.
    """
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        delete(MediaRequest)
        .where(
            MediaRequest.status == "available",
            MediaRequest.available_at.is_not(None),
            MediaRequest.available_at < cutoff,
        )
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()
    deleted = int(result.rowcount or 0)
    logger.info(
        "[requests-cleanup] deleted=%s days=%s cutoff=%s",
        deleted, days, cutoff.isoformat(),
    )
    return deleted
