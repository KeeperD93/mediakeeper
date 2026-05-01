"""
Notifications service — universal bell for the Portal module.

Used by the events flow today (invitation, accepted, declined, cancelled,
modified, removed, room_open, reminder) and ready to host future
demand-related notifs (request_approved, request_rejected, ticket_replied,
…).
"""
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import MKNotification

logger = logging.getLogger("mediakeeper.portal.notifications")


async def create(
    db: AsyncSession,
    user_id: int,
    notif_type: str,
    payload: dict | None = None,
) -> MKNotification:
    """
    Push a new notification onto a user's bell. Returns the persisted
    row so callers can broadcast it via WebSocket if they want a
    realtime push as well.
    """
    n = MKNotification(
        user_id=user_id,
        type=notif_type,
        payload=payload or {},
        read=False,
    )
    db.add(n)
    await db.flush()
    return n


async def create_many(
    db: AsyncSession,
    user_ids: list[int],
    notif_type: str,
    payload: dict | None = None,
) -> int:
    """Bulk insert. Used for public events that notify everyone."""
    if not user_ids:
        return 0
    rows = [
        MKNotification(
            user_id=uid,
            type=notif_type,
            payload=payload or {},
            read=False,
        )
        for uid in user_ids
    ]
    db.add_all(rows)
    await db.flush()
    return len(rows)


async def list_for_user(
    db: AsyncSession,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """Most recent notifications first. Limit caps at 50 by default."""
    q = select(MKNotification).where(MKNotification.user_id == user_id)
    if unread_only:
        q = q.where(MKNotification.read.is_(False))
    q = q.order_by(MKNotification.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "type": r.type,
            "payload": r.payload or {},
            "read": r.read,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def count_unread(db: AsyncSession, user_id: int) -> int:
    res = await db.execute(
        select(func.count(MKNotification.id)).where(
            MKNotification.user_id == user_id,
            MKNotification.read.is_(False),
        )
    )
    return int(res.scalar() or 0)


async def mark_read(db: AsyncSession, user_id: int, notif_id: int) -> bool:
    res = await db.execute(
        update(MKNotification)
        .where(
            MKNotification.id == notif_id,
            MKNotification.user_id == user_id,
        )
        .values(read=True)
    )
    return res.rowcount > 0


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    res = await db.execute(
        update(MKNotification)
        .where(
            MKNotification.user_id == user_id,
            MKNotification.read.is_(False),
        )
        .values(read=True)
    )
    return res.rowcount or 0


async def delete_old(db: AsyncSession, older_than_days: int = 30) -> int:
    """House-keeping helper for the scheduler — purges stale notifs."""
    cutoff = datetime.now(timezone.utc).timestamp() - older_than_days * 86400
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    res = await db.execute(
        delete(MKNotification).where(MKNotification.created_at < cutoff_dt)
    )
    return res.rowcount or 0
