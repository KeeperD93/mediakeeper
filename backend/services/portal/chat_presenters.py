"""Chat display-name lookup and message serialization."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.chat import ChatMessage
from models.portal.profile import UserProfile
from models.user import User


async def resolve_display_name(db: AsyncSession, user_id: int) -> str:
    """Return profile.display_name if available, fallback to User.username."""
    row = (
        await db.execute(
            select(UserProfile.display_name).where(UserProfile.user_id == user_id)
        )
    ).scalar_one_or_none()
    if row:
        return row
    row = (
        await db.execute(select(User.username).where(User.id == user_id))
    ).scalar_one_or_none()
    return row or f"#{user_id}"


def serialize_message(m: ChatMessage, user_name: str | None = None) -> dict:
    """Serialise a chat message for the API.

    Once a GDPR purge removes the original author, ``m.user_id`` is
    NULL (FK ``ON DELETE SET NULL``, migration 040). The frontend
    relies on the ``user_deleted`` flag to render an anonymous
    placeholder instead of the live username + avatar.
    """
    return {
        "id": m.id,
        "room_id": m.room_id,
        "user_id": m.user_id,
        "user_name": user_name if m.user_id is not None else None,
        "user_deleted": m.user_id is None,
        "content": m.content,
        "deleted": bool(getattr(m, "deleted", False)),
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
