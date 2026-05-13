"""Shared helpers for the MediaKeeper Events layer: constants, user label
resolver, event serializer, scheduling-conflict check."""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.event import MKEvent, MKEventInvitation
from models.portal.profile import UserProfile

logger = logging.getLogger("mediakeeper.portal.mk_events")

MAX_INVITE_RETRIES = 3
MAX_PARTICIPANTS = 50
ROOM_OPEN_BEFORE_MIN = 15


async def _user_label(db: AsyncSession, user_id: int | None) -> str | None:
    """Resolve a user_id to a display name (pseudo) for notif payloads.

    Returns ``None`` for a purged user (``user_id IS NULL``, FK
    ``SET NULL`` since migration 041) so callers can render a localised
    "Deleted user" placeholder instead of a fabricated ``user#None``
    string. A live user with no profile still falls back to the raw
    ``user#<id>`` marker — same semantics as before.
    """
    if user_id is None:
        return None
    res = await db.execute(
        select(UserProfile.display_name, User.username)
        .select_from(User)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(User.id == user_id)
    )
    row = res.first()
    if not row:
        return f"user#{user_id}"
    return row[0] or row[1] or f"user#{user_id}"


async def _serialize_event(db: AsyncSession, event: MKEvent) -> dict:
    """Plain-dict representation including invitations + creator pseudo."""
    inv_rows = (await db.execute(
        select(MKEventInvitation, User.username, UserProfile.display_name)
        .join(User, User.id == MKEventInvitation.user_id, isouter=True)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(MKEventInvitation.event_id == event.id)
    )).all()
    invitations = []
    for inv, username, display in inv_rows:
        invitations.append({
            "id": inv.id,
            "user_id": inv.user_id,
            "username": display or username or f"user#{inv.user_id}",
            "status": inv.status,
            "invite_count": inv.invite_count,
            "seat_index": inv.seat_index,
            "responded_at": inv.responded_at.isoformat() if inv.responded_at else None,
        })

    creator_label = await _user_label(db, event.creator_user_id)

    return {
        "id": event.id,
        "creator_user_id": event.creator_user_id,
        "creator_label": creator_label,
        # ``True`` once the creator has been GDPR-purged. Lets the UI
        # swap the label for the "Deleted user" placeholder without
        # extra round-trips.
        "creator_deleted": event.creator_user_id is None,
        "title": event.title,
        "kind": event.kind,
        "tmdb_ids": event.tmdb_ids or [],
        "scheduled_at": event.scheduled_at.isoformat() if event.scheduled_at else None,
        "comment": event.comment,
        "status": event.status,
        "room_opened_at": event.room_opened_at.isoformat() if event.room_opened_at else None,
        "current_step": event.current_step,
        "invitations": invitations,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None,
    }


async def _has_conflict(db: AsyncSession, user_id: int, scheduled_at: datetime) -> bool:
    """
    Approximate overlap check: returns True if the user is already
    accepted on another event whose start time is within ±2h of the
    new one. We don't store durations yet so a fixed window is the
    safest pragmatic approach.
    """
    window_start = scheduled_at - timedelta(hours=2)
    window_end = scheduled_at + timedelta(hours=2)
    res = await db.execute(
        select(func.count(MKEvent.id))
        .join(MKEventInvitation, MKEventInvitation.event_id == MKEvent.id)
        .where(
            MKEventInvitation.user_id == user_id,
            MKEventInvitation.status == "accepted",
            MKEvent.status == "scheduled",
            MKEvent.scheduled_at >= window_start,
            MKEvent.scheduled_at <= window_end,
        )
    )
    return int(res.scalar() or 0) > 0
