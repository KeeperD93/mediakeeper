"""Room chat — lightweight messaging persistent for 24h post-event."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.event import MKEvent, MKEventInvitation, MKEventMessage
from models.portal.profile import UserProfile


async def list_messages(
    db: AsyncSession,
    event_id: int,
    user_id: int | None = None,
    limit: int = 200,
) -> dict:
    if user_id is not None:
        event = (await db.execute(
            select(MKEvent).where(MKEvent.id == event_id)
        )).scalar_one_or_none()
        if not event:
            return {"error": "not_found"}

        inv = (await db.execute(
            select(MKEventInvitation).where(
                MKEventInvitation.event_id == event_id,
                MKEventInvitation.user_id == user_id,
                MKEventInvitation.status == "accepted",
            )
        )).scalar_one_or_none()
        if not inv:
            return {"error": "not_member"}

    rows = (await db.execute(
        select(MKEventMessage, User.username, UserProfile.display_name)
        .join(User, User.id == MKEventMessage.user_id, isouter=True)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(MKEventMessage.event_id == event_id)
        .order_by(MKEventMessage.sent_at.asc())
        .limit(limit)
    )).all()
    # ``user_id`` is nullable since migration 041 (``ON DELETE SET NULL``):
    # surface a ``user_deleted`` flag so the frontend can render the
    # "Deleted user" placeholder, mirroring ``chat_presenters.serialize_message``.
    return {"items": [
        {
            "id": m.id,
            "user_id": m.user_id,
            "username": (
                None
                if m.user_id is None
                else (display or username or f"user#{m.user_id}")
            ),
            "user_deleted": m.user_id is None,
            "content": m.content,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
        }
        for m, username, display in rows
    ]}


async def post_message(
    db: AsyncSession,
    event_id: int,
    user_id: int,
    content: str,
) -> dict:
    """Sanity check: only accepted members can post."""
    inv = (await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == user_id,
            MKEventInvitation.status == "accepted",
        )
    )).scalar_one_or_none()
    if not inv:
        return {"error": "not_member"}

    msg = MKEventMessage(
        event_id=event_id,
        user_id=user_id,
        content=content[:2000],
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return {
        "id": msg.id,
        "user_id": user_id,
        "content": msg.content,
        "sent_at": msg.sent_at.isoformat(),
    }
