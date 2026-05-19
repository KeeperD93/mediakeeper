"""Cinema-room entry — seat allocation under a row lock."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import MKEvent, MKEventInvitation
from services.portal.mk_events_utils import (
    MAX_PARTICIPANTS,
    ROOM_OPEN_BEFORE_MIN,
    _count_seated,
    _serialize_event,
    is_event_terminated,
)


async def enter_room(
    db: AsyncSession,
    event_id: int,
    user_id: int,
) -> dict:
    """
    User signals they entered the cinema room. Returns their seat
    index (allocated on first entry, persisted afterwards) and the
    event's full state. Reachable only ROOM_OPEN_BEFORE_MIN minutes
    before scheduled_at and beyond.

    The ``MKEvent`` row is locked via ``SELECT ... FOR UPDATE`` so the
    open-window check → membership check → free-seat scan → seat
    assignment → ``room_opened_at`` stamp run as a single atomic
    sequence. Two concurrent enter_room calls on the same event cannot
    pick the same seat under PostgreSQL. SQLite accepts ``FOR UPDATE``
    as a no-op; the session-level transaction state still acts as the
    invariant the tests pin down. Every non-success exit after the lock
    rolls back so the row lock is released before the function returns.
    """
    event = (await db.execute(
        select(MKEvent)
        .where(MKEvent.id == event_id)
        .with_for_update()
    )).scalar_one_or_none()
    if not event:
        await db.rollback()
        return {"error": "not_found"}

    now = datetime.now(timezone.utc)
    open_at = event.scheduled_at - timedelta(minutes=ROOM_OPEN_BEFORE_MIN)
    if now < open_at:
        await db.rollback()
        return {"error": "room_not_open", "open_at": open_at.isoformat()}
    # Hard time-based cutoff: an event nobody marked ``done`` (no
    # autonomous closer job exists today) used to stay reachable
    # forever. After ``ROOM_CLOSE_AFTER_HOURS`` past ``scheduled_at``,
    # the room is closed for new entries even if the status row is
    # still ``scheduled``.
    if is_event_terminated(event, now):
        await db.rollback()
        return {"error": "event_ended"}

    inv = (await db.execute(
        select(MKEventInvitation)
        .where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == user_id,
            MKEventInvitation.status == "accepted",
        )
        .with_for_update()
    )).scalar_one_or_none()
    if not inv:
        await db.rollback()
        return {"error": "not_member"}

    # Per-event capacity replaces the legacy 50-seat pool. The
    # admin-tunable bounds are enforced at create time; this clamp is
    # a defensive guard against rows imported from a legacy schema
    # without ``max_participants`` populated.
    capacity = int(event.max_participants or 0)
    if capacity <= 0:
        capacity = MAX_PARTICIPANTS
    capacity = min(capacity, MAX_PARTICIPANTS)

    first_entry = inv.seat_index is None
    if not first_entry and inv.seat_index >= capacity:
        # Soft remap: an earlier entry was allocated a seat past the
        # current capacity (admin lowered the cap, or legacy 50-seat
        # row). Reassign as if it were a fresh entry so the layout
        # stays inside the new bounds.
        inv.seat_index = None
        first_entry = True

    if first_entry:
        seated = await _count_seated(db, event_id)
        if seated >= capacity:
            await db.rollback()
            return {"error": "room_full"}
        # Sequential allocation: the next entrant gets the next free
        # index (0..capacity-1). Combined with ``_compact_seats`` on
        # decline / remove, this keeps the seated avatars at the
        # centre of the layout — see ``mk_events_utils``.
        inv.seat_index = seated
        # Latecomer seed: a first-time entrant inherits the group-wide
        # ``current_step`` so the launch CTA points at the film the
        # group is currently watching. Per-user advance from there.
        inv.user_step = event.current_step or 0

    # Heartbeat stamp — peers see the avatar appear right away (or
    # re-appear, on a return visit) without waiting for the next
    # explicit heartbeat tick from the front-end.
    inv.last_seen_at = now
    db.add(inv)

    if event.room_opened_at is None:
        event.room_opened_at = now
        db.add(event)

    await db.commit()
    return {
        "ok": True,
        "seat_index": inv.seat_index,
        "event": await _serialize_event(db, event),
    }
