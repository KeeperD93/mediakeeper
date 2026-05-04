"""Notification history + rules/DND sub-router.

Split out of ``api/notifications.py`` to keep each file under 300 lines.
Mounted as a sub-router on the main notifications router so URLs stay
``/api/notifications/history`` and ``/api/notifications/rules``.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.pagination import decode_cursor, build_cursor_response
from models.notification_log import NotificationLog
from models.user import User
from api.auth import get_current_user
from services.settings import get_notification_channel, set_notification_channel

router = APIRouter(tags=["notifications"])


class LogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    channel: str = "discord"
    webhook_name: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    status: str = "sent"
    error: Optional[str] = None


class LogRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: List[LogEntry]


@router.get("/history")
async def get_history(
    limit: int = 100,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    cursor: str = "",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(NotificationLog).order_by(NotificationLog.id.desc())
    if channel:
        q = q.where(NotificationLog.channel == channel)
    if status:
        q = q.where(NotificationLog.status == status)

    # Count total (with filters)
    count_q = select(func.count(NotificationLog.id))
    if channel:
        count_q = count_q.where(NotificationLog.channel == channel)
    if status:
        count_q = count_q.where(NotificationLog.status == status)
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    # Cursor
    decoded = decode_cursor(cursor)
    if decoded and "id" in decoded:
        q = q.where(NotificationLog.id < decoded["id"])

    result = await db.execute(q.limit(limit + 1))
    rows = result.scalars().all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [
        {"id": r.id, "event_type": r.event_type, "channel": r.channel, "webhook_name": r.webhook_name,
         "title": r.title, "message": r.message, "status": r.status, "error": r.error,
         "sent_at": r.sent_at.isoformat() if r.sent_at else None}
        for r in rows
    ]
    return build_cursor_response(items, total, limit, cursor_field="id", has_more=has_more)


@router.get("/history/stats")
async def get_history_stats(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    sent = await db.execute(select(func.count(NotificationLog.id)).where(NotificationLog.status == "sent"))
    failed = await db.execute(select(func.count(NotificationLog.id)).where(NotificationLog.status == "failed"))
    total = await db.execute(select(func.count(NotificationLog.id)))
    return {"total": total.scalar() or 0, "sent": sent.scalar() or 0, "failed": failed.scalar() or 0}


@router.post("/history/add")
async def add_history(req: LogRequest, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    for e in req.entries:
        db.add(NotificationLog(event_type=e.event_type, channel=e.channel, webhook_name=e.webhook_name,
                               title=e.title, message=e.message, status=e.status, error=e.error))
    await db.commit()
    return {"success": True}


@router.delete("/history")
async def clear_history(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await db.execute(delete(NotificationLog))
    await db.commit()
    return {"success": True}


# ---- Rules & DND config (stored in notification_channels as JSON) ----

class NotifRulesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dnd_enabled: bool = False
    dnd_start: str = "23:00"  # HH:MM
    dnd_end: str = "07:00"
    library_filter: list = Field(default_factory=list)  # empty = all
    min_resolution: str = ""  # "", "720p", "1080p", "4K"
    genre_filter: list = Field(default_factory=list)


@router.get("/rules")
async def get_rules(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    val = await get_notification_channel(db, "notif_rules")
    if val:
        try:
            return json.loads(val)
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
    return NotifRulesConfig().model_dump() if hasattr(NotifRulesConfig, 'model_dump') else NotifRulesConfig().dict()


@router.post("/rules")
async def save_rules(req: NotifRulesConfig, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    data_str = req.model_dump_json() if hasattr(req, 'model_dump_json') else req.json()
    await set_notification_channel(db, "notif_rules", data_str)
    return {"success": True}
