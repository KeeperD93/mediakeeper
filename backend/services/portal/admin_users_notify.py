"""Targeted admin → user notification.

Drops a row in ``mk_notifications`` so the user sees a bell update on
their next ping. Body is stored as ``payload.message`` and the type is
fixed to ``admin_message`` so the front knows how to render the toast
header (admin-flagged, no avatar of a sender, etc.).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import MKNotification

from .admin_users_audit import record_audit
from .admin_users_constants import ACTION_USER_NOTIFICATION_SENT


NOTIFICATION_TYPE_ADMIN_MESSAGE = "admin_message"


async def send_admin_notification(
    db: AsyncSession,
    *,
    target_user_id: int,
    title: str,
    body: str,
    admin_user_id: int | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    title = (title or "").strip()[:120]
    body = (body or "").strip()[:1000]
    if not title or not body:
        return {"error": "empty"}

    notif = MKNotification(
        user_id=target_user_id,
        type=NOTIFICATION_TYPE_ADMIN_MESSAGE,
        payload={"title": title, "body": body, "from_admin": True},
        read=False,
    )
    db.add(notif)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        action=ACTION_USER_NOTIFICATION_SENT,
        payload={"title": title, "len": len(body)},
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"ok": True}
