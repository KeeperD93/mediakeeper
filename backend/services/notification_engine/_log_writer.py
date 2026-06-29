"""Write NotificationLog rows (success/failure) to the DB."""
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.notification_log import NotificationLog

logger = logging.getLogger("mediakeeper.notifications")


async def log_sent(
    db: AsyncSession,
    *,
    event_type: str,
    webhook_name: str,
    title: str,
    message: str,
    channel: str = "discord",
) -> None:
    try:
        db.add(NotificationLog(
            event_type=event_type,
            channel=channel,
            webhook_name=webhook_name,
            title=title,
            message=message,
            status="sent",
            error=None,
            sent_at=datetime.now(timezone.utc),
        ))
        await db.commit()
    except Exception as le:
        logger.error("[NOTIFICATIONS] Error write history: %s", le, exc_info=True)
        await db.rollback()


async def log_failed(
    db: AsyncSession,
    *,
    event_type: str,
    webhook_name: str,
    title: str,
    message: str,
    error: str,
    channel: str = "discord",
) -> None:
    try:
        db.add(NotificationLog(
            event_type=event_type,
            channel=channel,
            webhook_name=webhook_name,
            title=title,
            message=message,
            status="failed",
            error=error,
            sent_at=datetime.now(timezone.utc),
        ))
        await db.commit()
    except Exception:
        await db.rollback()
