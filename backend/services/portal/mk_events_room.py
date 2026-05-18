"""Cinema-room entry — seat allocation under a row lock."""
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import MKEvent, MKEventInvitation
from services.portal.mk_events_utils import (
    MAX_PARTICIPANTS, ROOM_OPEN_BEFORE_MIN,
    _serialize_event, is_event_terminated,
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

    first_entry = inv.seat_index is None
    if first_entry:
        # Assign a free seat at random under the row lock so two concurrent
        # callers cannot pick the same seat.
        taken = (await db.execute(
            select(MKEventInvitation.seat_index).where(
                MKEventInvitation.event_id == event_id,
                MKEventInvitation.seat_index.isnot(None),
            )
        )).scalars().all()
        free = [i for i in range(MAX_PARTICIPANTS) if i not in set(taken)]
        if not free:
            await db.rollback()
            return {"error": "room_full"}
        inv.seat_index = random.choice(free)  # noqa: S311 -- random seat assignment in a virtual cinema room, no security purpose
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
