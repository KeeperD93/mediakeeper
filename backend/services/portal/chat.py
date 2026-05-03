"""Chat system: rooms, messages, mutes."""
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.chat import ChatRoom, ChatMessage
from models.portal.profile import UserProfile
from core.pagination import decode_cursor, build_cursor_response
from services.portal import strip_tags_and_trim
from services.portal.chat_mutes import is_muted
from services.portal.chat_presenters import resolve_display_name, serialize_message

logger = logging.getLogger("mediakeeper.portal.chat")


async def get_or_create_room(
    db: AsyncSession,
    room_type: str,
    name: str,
    linked_request_id: int | None = None,
) -> ChatRoom:
    """Get existing room or create one."""
    query = select(ChatRoom).where(ChatRoom.type == room_type, ChatRoom.name == name)
    if linked_request_id:
        query = query.where(ChatRoom.linked_request_id == linked_request_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    if room:
        return room

    room = ChatRoom(
        type=room_type, name=name,
        linked_request_id=linked_request_id,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


DEFAULT_LOUNGE_NAME = "lounge"


async def _ensure_default_lounge(db: AsyncSession) -> None:
    """Make sure a global lounge room exists.

    Without it the FAB chat can't bind to anything (``rooms`` is empty),
    so the user only ever sees "no messages" and can't even send one.
    Creating it on first read is idempotent and keeps the migration
    layer free of seed data.
    """
    existing = (
        await db.execute(
            select(ChatRoom).where(
                ChatRoom.type == "lounge",
                ChatRoom.name == DEFAULT_LOUNGE_NAME,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return
    db.add(ChatRoom(type="lounge", name=DEFAULT_LOUNGE_NAME))
    await db.commit()


async def list_rooms(db: AsyncSession) -> list[dict]:
    """List all chat rooms (creating the default lounge on first call)."""
    await _ensure_default_lounge(db)
    result = await db.execute(
        select(ChatRoom).order_by(ChatRoom.id)
    )
    return [{
        "id": r.id, "type": r.type, "name": r.name,
        "linked_request_id": r.linked_request_id,
    } for r in result.scalars().all()]


async def get_unread_count(db: AsyncSession, user_id: int) -> dict:
    """Return the number of chat messages unread by ``user_id``.

    "Unread" = not authored by the user, not deleted, and with an id
    greater than the user's persisted ``chat_last_read_message_id``.
    Authored messages are excluded so a user's own posts never bump
    their own badge.
    """
    profile = (
        await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
    ).scalar_one_or_none()
    last_read = (profile.chat_last_read_message_id if profile else None) or 0

    count_q = select(func.count(ChatMessage.id)).where(
        ChatMessage.id > last_read,
        ChatMessage.user_id != user_id,
        ChatMessage.deleted == False,  # noqa: E712
    )
    unread = (await db.execute(count_q)).scalar() or 0

    latest_id = (
        await db.execute(select(func.max(ChatMessage.id)))
    ).scalar() or 0

    return {"unread": int(unread), "latest_message_id": int(latest_id)}


async def mark_room_read(db: AsyncSession, user_id: int) -> dict:
    """Persist the latest message id as read for ``user_id``.

    We snap to the current ``MAX(chat_messages.id)`` rather than to the
    last id the client knows about — keeps the implementation simple
    while staying race-safe (a message that lands during the round trip
    will simply count as unread, and the next poll catches it).
    """
    latest_id = (
        await db.execute(select(func.max(ChatMessage.id)))
    ).scalar() or 0

    profile = (
        await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
    ).scalar_one_or_none()
    if not profile:
        return {"success": False, "error": "profile_not_found"}

    profile.chat_last_read_message_id = int(latest_id)
    db.add(profile)
    await db.commit()
    return {"success": True, "latest_message_id": int(latest_id)}


async def send_message(
    db: AsyncSession,
    room_id: int,
    user_id: int,
    content: str,
) -> dict:
    """Send a message to a room."""
    if await is_muted(db, user_id):
        return {"error": "muted"}

    msg = ChatMessage(
        room_id=room_id,
        user_id=user_id,
        content=strip_tags_and_trim(content, 2000),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    # Eagerly resolve the author's display name so the websocket
    # broadcast already carries it — clients don't have to do a second
    # lookup per message.
    name = await resolve_display_name(db, user_id)
    return {
        "success": True,
        "message": serialize_message(msg, user_name=name),
    }


async def get_messages(
    db: AsyncSession,
    room_id: int,
    cursor: str | None = None,
    limit: int = 50,
) -> dict:
    """Get messages for a room with cursor pagination."""
    query = (
        select(ChatMessage)
        .where(ChatMessage.room_id == room_id, ChatMessage.deleted == False)  # noqa: E712
        .order_by(ChatMessage.id.desc())
    )
    count_q = select(func.count(ChatMessage.id)).where(
        ChatMessage.room_id == room_id,
        ChatMessage.deleted == False,  # noqa: E712
    )

    cursor_data = decode_cursor(cursor)
    if cursor_data and cursor_data.get("id"):
        query = query.where(ChatMessage.id < cursor_data["id"])

    total = (await db.execute(count_q)).scalar() or 0
    raw = (await db.execute(query.limit(limit))).scalars().all()

    # Resolve every author's display_name in a single SELECT rather
    # than N+1 lookups while serialising.
    user_ids = list({m.user_id for m in raw})
    name_map: dict[int, str] = {}
    if user_ids:
        prof_rows = (
            await db.execute(
                select(UserProfile.user_id, UserProfile.display_name)
                .where(UserProfile.user_id.in_(user_ids))
            )
        ).all()
        name_map = {uid: name for uid, name in prof_rows}

    items = [serialize_message(m, user_name=name_map.get(m.user_id)) for m in raw]
    return build_cursor_response(items, total, limit)


async def delete_message(
    db: AsyncSession, message_id: int, user_id: int, is_admin: bool = False
) -> dict:
    """
    Soft-delete a message.

    Rules:
    - Admins can delete any message at any time.
    - Regular users can only delete their own messages, and only within
      a 60-second window after posting. This matches the UX contract
      shown in the FAB chat (countdown on the delete button).
    """
    msg = await db.get(ChatMessage, message_id)
    if not msg:
        return {"error": "not_found"}
    if is_admin:
        msg.deleted = True
        db.add(msg)
        await db.commit()
        return {"success": True}
    if msg.user_id != user_id:
        return {"error": "forbidden"}
    # 60-second grace window for self-delete.
    now = datetime.now(timezone.utc)
    created = msg.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if created and (now - created).total_seconds() > 60:
        return {"error": "delete_window_expired"}
    msg.deleted = True
    db.add(msg)
    await db.commit()
    return {"success": True}


async def report_message(
    db: AsyncSession, message_id: int, reporter_id: int, reason: str | None = None
) -> dict:
    """
    Flag a chat message for moderator attention.

    - Silently idempotent: if the same user already reported this
      message, we don't create a second row (avoid spam).
    - Fires a notification to MediaKeeper admins through the shared
      notifications table (the bell on the dashboard).
    """
    from models.portal.chat import ChatReport

    msg = await db.get(ChatMessage, message_id)
    if not msg:
        return {"error": "not_found"}

    existing = (
        await db.execute(
            select(ChatReport).where(
                ChatReport.message_id == message_id,
                ChatReport.reporter_id == reporter_id,
                ChatReport.handled.is_(False),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return {"success": True, "already_reported": True}

    report = ChatReport(
        message_id=message_id,
        reporter_id=reporter_id,
        reason=reason,
    )
    db.add(report)
    await db.flush()

    # Push a Portal-bell notification to every admin and moderator so
    # the report shows up next to event/request notifs without forcing
    # them to open the MediaKeeper admin dashboard. The MK admin bell
    # still polls ``/chat/reports`` for a global moderation queue —
    # this addition mirrors the alert into the Portal bell only.
    from services.portal import notifications as notifs

    reporter_profile = (
        await db.execute(
            select(UserProfile).where(UserProfile.user_id == reporter_id)
        )
    ).scalar_one_or_none()
    mod_ids_q = await db.execute(
        select(UserProfile.user_id).where(
            UserProfile.role.in_(("admin", "moderator")),
            UserProfile.account_active.is_(True),
        )
    )
    mod_ids = [uid for (uid,) in mod_ids_q.all() if uid != reporter_id]
    if mod_ids:
        await notifs.create_many(
            db,
            mod_ids,
            "chat_message_reported",
            payload={
                "report_id": report.id,
                "message_id": message_id,
                "reporter_name": (reporter_profile.display_name
                                  if reporter_profile else None),
                "excerpt": (msg.content or "")[:120],
            },
        )

    await db.commit()
    return {"success": True, "report_id": report.id}
