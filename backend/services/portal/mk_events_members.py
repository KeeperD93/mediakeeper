"""Event membership — invite, accept/decline, remove a user."""
import logging
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from constants.notifications import (
    NOTIF_EVENT_ACCEPTED,
    NOTIF_EVENT_DECLINED,
    NOTIF_EVENT_INVITATION,
    NOTIF_EVENT_REMOVED,
)
from models.portal.event import InvitationStatus, MKEvent, MKEventInvitation
from services.portal import notifications as notifs
from services.portal.mk_events_utils import (
    MAX_INVITE_RETRIES,
    _compact_seats,
    _has_conflict,
    _user_label,
    is_event_terminated,
    is_invitable,
)

logger = logging.getLogger("mediakeeper.portal.mk_events_members")


async def _load_invitation(
    db: AsyncSession, event_id: int, user_id: int,
) -> MKEventInvitation | None:
    """Lookup helper isolated so concurrency tests can monkeypatch it to
    drive the real INSERT path through ``uq_mk_event_invitation``."""
    result = await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


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
    if not await is_invitable(db, invitee_user_id):
        return {"error": "not_invitable"}

    inv = await _load_invitation(db, event_id, invitee_user_id)

    if inv is None:
        # First-time invitation. SAVEPOINT keeps the outer transaction
        # usable when a concurrent peer wins the race on
        # ``uq_mk_event_invitation`` — we reload the winning row instead
        # of leaking the IntegrityError on the session.
        try:
            async with db.begin_nested():
                inv = MKEventInvitation(
                    event_id=event_id,
                    user_id=invitee_user_id,
                    status=InvitationStatus.PENDING.value,
                    invite_count=1,
                )
                db.add(inv)
                await db.flush()
        except IntegrityError:
            logger.debug(
                "[MKEVENT] invite race avoided event_id=%s "
                "invitee_user_id=%s — concurrent insert won",
                event_id, invitee_user_id,
            )
            existing = await _load_invitation(db, event_id, invitee_user_id)
            if existing is None:
                # Should not happen — the unique constraint just fired.
                await db.rollback()
                return {"error": "conflict"}
            if existing.status == InvitationStatus.ACCEPTED.value:
                await db.rollback()
                return {"error": "already_accepted"}
            if existing.status == InvitationStatus.REMOVED.value:
                await db.rollback()
                return {"error": "removed_user"}
            # Concurrent peer already inserted + notified the invitee.
            # Skip the notification to avoid the duplicate, finalise the
            # outer transaction, and return success.
            await db.commit()
            return {"ok": True}

        creator_label = await _user_label(db, creator_user_id)
        await notifs.create(db, invitee_user_id, NOTIF_EVENT_INVITATION, {
            "event_id": event.id,
            "title": event.title,
            "kind": event.kind,
            "scheduled_at": event.scheduled_at.isoformat(),
            "from": creator_label,
        })
        await db.commit()
        return {"ok": True}

    # Re-invitation path — existing row.
    if inv.status == InvitationStatus.ACCEPTED.value:
        return {"error": "already_accepted"}
    if inv.status == InvitationStatus.REMOVED.value:
        return {"error": "removed_user"}
    if inv.invite_count >= MAX_INVITE_RETRIES:
        return {"error": "max_retries_reached"}

    # Atomic SQL increment guarded by the cap. Two parallel re-invites
    # cannot drop an increment: the keyed UPDATE reads the live DB value
    # (``invite_count + 1``) and the ``WHERE invite_count < cap`` clause
    # serialises the cap check at the SQL level. If the row was meanwhile
    # accepted/removed or hit the cap, ``rowcount`` is 0 and we surface
    # the up-to-date error after a fresh reload.
    upd = await db.execute(
        update(MKEventInvitation)
        .where(
            MKEventInvitation.id == inv.id,
            MKEventInvitation.invite_count < MAX_INVITE_RETRIES,
            MKEventInvitation.status.notin_(
                (InvitationStatus.ACCEPTED.value, InvitationStatus.REMOVED.value)
            ),
        )
        .values(
            status=InvitationStatus.PENDING.value,
            invite_count=MKEventInvitation.invite_count + 1,
            responded_at=None,
        )
        .execution_options(synchronize_session=False)
    )
    if (upd.rowcount or 0) == 0:
        await db.rollback()
        fresh = await _load_invitation(db, event_id, invitee_user_id)
        if fresh is not None:
            if fresh.status == InvitationStatus.ACCEPTED.value:
                return {"error": "already_accepted"}
            if fresh.status == InvitationStatus.REMOVED.value:
                return {"error": "removed_user"}
        return {"error": "max_retries_reached"}

    creator_label = await _user_label(db, creator_user_id)
    await notifs.create(db, invitee_user_id, NOTIF_EVENT_INVITATION, {
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

    # Accepts on a stale / cancelled / past-cutoff event are pointless
    # and used to drag the user straight into a dead cinema room. The
    # decline path stays open so a viewer can still tidy up a stale
    # notification.
    if decision == "accept" and is_event_terminated(event):
        return {"error": "event_ended"}

    inv = await _load_invitation(db, event_id, user_id)

    # Public event auto-creates an invitation row when the user accepts
    # for the first time (they were notified but not pre-listed). The
    # SAVEPOINT keeps the outer session usable when a concurrent peer
    # wins the race on ``uq_mk_event_invitation``.
    if inv is None:
        if event.kind != "public":
            return {"error": "not_invited"}
        try:
            async with db.begin_nested():
                inv = MKEventInvitation(
                    event_id=event_id,
                    user_id=user_id,
                    status=InvitationStatus.PENDING.value,
                    invite_count=1,
                )
                db.add(inv)
                await db.flush()
        except IntegrityError:
            logger.debug(
                "[MKEVENT] respond race avoided event_id=%s "
                "user_id=%s — concurrent insert won",
                event_id, user_id,
            )
            inv = await _load_invitation(db, event_id, user_id)
            if inv is None:
                await db.rollback()
                return {"error": "conflict"}
            # Fall through with the winning row — apply the user's
            # decision on top of it (typically pending → accepted).

    if inv.status == InvitationStatus.REMOVED.value:
        return {"error": "removed_user"}

    inv.status = (
        InvitationStatus.ACCEPTED.value if decision == "accept"
        else InvitationStatus.DECLINED.value
    )
    inv.responded_at = datetime.now(timezone.utc)
    if decision == "decline":
        # Free the seat (if any) and compact the layout so the remaining
        # avatars keep their centered grid placement — see option B
        # rebalance contract in ``mk_events_utils._compact_seats``.
        inv.seat_index = None
        inv.last_seen_at = None
    db.add(inv)
    if decision == "decline":
        await _compact_seats(db, event_id)

    # Conflict warning when accepting (we don't block, just inform).
    # Exclude the event being accepted from the count — its invitation
    # row was just flipped to ``accepted`` above and would otherwise
    # show up as a self-collision in the read-your-writes view.
    conflict_warning = False
    if decision == "accept":
        conflict_warning = await _has_conflict(
            db, user_id, event.scheduled_at, exclude_event_id=event.id,
        )

    user_label = await _user_label(db, user_id)
    notif_type = NOTIF_EVENT_ACCEPTED if decision == "accept" else NOTIF_EVENT_DECLINED
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

    inv.status = InvitationStatus.REMOVED.value
    # Same housekeeping as a self-decline: release the seat + clear
    # presence so the centred layout stays contiguous after the
    # creator boots a member.
    inv.seat_index = None
    inv.last_seen_at = None
    db.add(inv)
    await _compact_seats(db, event_id)
    await notifs.create(db, member_user_id, NOTIF_EVENT_REMOVED, {
        "event_id": event.id,
        "title": event.title,
    })
    await db.commit()
    return {"ok": True}
