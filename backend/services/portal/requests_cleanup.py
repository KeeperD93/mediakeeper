"""Hygiene job: archive ``available`` media requests older than N days.

Gated by the ``requests.auto_cleanup_days`` setting (0 = disabled). Archived
requests leave the Requests lists but stay in the table, so every total,
statistic and trophy keeps counting them. The scheduler invokes
:func:`archive_old_available_requests` once per day.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from constants.requests import REQUEST_AVAILABLE
from models.portal.request import MediaRequest
from services.settings import get_setting

logger = logging.getLogger("mediakeeper.portal.requests_cleanup")

# Named after the former deletion job; kept because every install stores it.
REQUESTS_AUTO_CLEANUP_KEY = "requests.auto_cleanup_days"


async def get_cleanup_days(db: AsyncSession) -> int:
    """Read the configured archive delay, in days. 0 (or invalid) = disabled."""
    raw = await get_setting(db, REQUESTS_AUTO_CLEANUP_KEY)
    if not raw:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def archive_old_available_requests(
    db: AsyncSession, *, days: int
) -> int:
    """Archive ``available`` requests with ``available_at`` older than ``days``.

    Returns the number of rows archived. When ``days <= 0`` the function
    is a no-op (disabled) — no query is issued. Rows whose ``available_at``
    is NULL are skipped (their age is unknown), and ``updated_at`` is kept
    so archiving never shows up as activity in the weekly counters.
    """
    if days <= 0:
        return 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    result = await db.execute(
        update(MediaRequest)
        .where(
            MediaRequest.status == REQUEST_AVAILABLE,
            MediaRequest.archived_at.is_(None),
            MediaRequest.available_at.is_not(None),
            MediaRequest.available_at < cutoff,
        )
        .values(archived_at=now, updated_at=MediaRequest.updated_at)
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()
    archived = int(result.rowcount or 0)
    logger.info(
        "[requests-cleanup] archived=%s days=%s cutoff=%s",
        archived, days, cutoff.isoformat(),
    )
    return archived
