"""Chat display-name lookup and message serialization."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.chat import ChatMessage
from models.portal.profile import UserProfile
from services.portal._display_name import resolve_display_name


async def chat_user_display_name(
    db: AsyncSession, user_id: int, lang: str = "fr"
) -> str:
    """Resolve a portal-safe display name for ``user_id``.

    Returns the user's chosen pseudo when one has been picked, otherwise
    the localized anonymous alias (the raw Emby ``username``
    must never reach a third-party portal viewer).
    """
    row = (
        await db.execute(
            select(
                UserProfile.display_name,
                UserProfile.display_name_must_set,
                UserProfile.role,
            )
            .where(UserProfile.user_id == user_id)
        )
    ).first()
    if row is None:
        return resolve_display_name(None, user_id, lang)
    display_name, must_set, role = row
    effective = None if must_set else display_name
    return resolve_display_name(effective, user_id, lang, is_admin=role == "admin")


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
