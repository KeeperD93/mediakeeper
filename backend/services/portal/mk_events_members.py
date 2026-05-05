"""Event membership — invite, accept/decline, remove, enter the cinema room."""
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import MKEvent, MKEventInvitation
from services.portal import notifications as notifs
from services.portal.mk_events_utils import (
    MAX_INVITE_RETRIES, MAX_PARTICIPANTS, ROOM_OPEN_BEFORE_MIN,
    _user_label, _serialize_event, _has_conflict,
)


async def invite_user(
    db: AsyncSession,
    event_id: int,
    creator_user_id: int,
    invitee_user_id: int,
) -> dict:
    """
    Adds (or re-invites) a user. Only the creator can call this.
    Re-invitations are capped at MAX_INVITE_RETRIES per user.
    """
    event = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"error": "not_found"}
    if event.creator_user_id != creator_user_id:
        return {"error": "forbidden"}

    inv = (await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == invitee_user_id,
        )
    )).scalar_one_or_none()

    if inv is None:
        inv = MKEventInvitation(
            event_id=event_id,
            user_id=invitee_user_id,
            status="pending",
            invite_count=1,
        )
        db.add(inv)
    else:
        if inv.status == "accepted":
            return {"error": "already_accepted"}
        if inv.status == "removed":
            return {"error": "removed_user"}
        if inv.invite_count >= MAX_INVITE_RETRIES:
            return {"error": "max_retries_reached"}
        inv.status = "pending"
        inv.invite_count += 1
        inv.responded_at = None
        db.add(inv)

    creator_label = await _user_label(db, creator_user_id)
    await notifs.create(db, invitee_user_id, "event_invitation", {
        "event_id": event.id,
        "title": event.title,
        "kind": event.kind,
        "scheduled_at": event.scheduled_at.isoformat(),
        "from": creator_label,
    })
    await db.commit()
    return {"ok": True}


async def respond(
    db: AsyncSession,
    event_id: int,
    user_id: int,
    decision: str,
) -> dict:
    """User accepts or declines an invitation. Notifies the creator."""
    if decision not in ("accept", "decline"):
        return {"error": "invalid_decision"}

    event = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"error": "not_found"}

    inv = (await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == user_id,
        )
    )).scalar_one_or_none()

    # Public event auto-creates an invitation row when the user accepts
    # for the first time (they were notified but not pre-listed).
    if inv is None:
        if event.kind != "public":
            return {"error": "not_invited"}
        inv = MKEventInvitation(
            event_id=event_id,
            user_id=user_id,
            status="pending",
            invite_count=1,
        )
        db.add(inv)
        await db.flush()

    if inv.status == "removed":
        return {"error": "removed_user"}

    inv.status = "accepted" if decision == "accept" else "declined"
    inv.responded_at = datetime.now(timezone.utc)
    db.add(inv)

    # Conflict warning when accepting (we don't block, just inform).
    conflict_warning = False
    if decision == "accept":
        conflict_warning = await _has_conflict(db, user_id, event.scheduled_at)

    user_label = await _user_label(db, user_id)
    notif_type = "event_accepted" if decision == "accept" else "event_declined"
    await notifs.create(db, event.creator_user_id, notif_type, {
        "event_id": event.id,
        "title": event.title,
        "from": user_label,
    })
    await db.commit()
    return {"ok": True, "conflict": conflict_warning}


async def remove_member(
    db: AsyncSession,
    event_id: int,
    creator_user_id: int,
    member_user_id: int,
) -> dict:
    event = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"error": "not_found"}
    if event.creator_user_id != creator_user_id:
        return {"error": "forbidden"}
    if member_user_id == creator_user_id:
        return {"error": "cannot_remove_creator"}

    inv = (await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == member_user_id,
        )
    )).scalar_one_or_none()
    if not inv:
        return {"error": "not_invited"}

    inv.status = "removed"
    db.add(inv)
    await notifs.create(db, member_user_id, "event_removed", {
        "event_id": event.id,
        "title": event.title,
    })
    await db.commit()
    return {"ok": True}


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
    """
    event = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"error": "not_found"}

    now = datetime.now(timezone.utc)
    open_at = event.scheduled_at - timedelta(minutes=ROOM_OPEN_BEFORE_MIN)
    if now < open_at:
        return {"error": "room_not_open", "open_at": open_at.isoformat()}

    inv = (await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == user_id,
            MKEventInvitation.status == "accepted",
        )
    )).scalar_one_or_none()
    if not inv:
        return {"error": "not_member"}

    if inv.seat_index is None:
        # Assign a free seat at random.
        taken = (await db.execute(
            select(MKEventInvitation.seat_index).where(
                MKEventInvitation.event_id == event_id,
                MKEventInvitation.seat_index.isnot(None),
            )
        )).scalars().all()
        free = [i for i in range(MAX_PARTICIPANTS) if i not in set(taken)]
        if not free:
            return {"error": "room_full"}
        inv.seat_index = random.choice(free)  # noqa: S311 -- random seat assignment in a virtual cinema room, no security purpose
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
