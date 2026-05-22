"""Cinema-room presence + per-user marathon advance.

These three flows share the same primary key (``MKEventInvitation`` of
``(event_id, user_id)``) and the same access guards (membership +
non-terminated event), so they live together:

* ``heartbeat`` — bumps ``last_seen_at`` so peers keep seeing the
  viewer's avatar in the seats UI.
* ``leave_room`` — clears ``last_seen_at`` so the seat row is kept
  (preserving the ``seat_index`` for a return visit) but the avatar
  disappears immediately for peers.
* ``advance_self_step`` — bumps the viewer's own ``user_step`` and
  re-syncs ``MKEvent.current_step`` to ``max(user_step)`` so the
  group-wide marathon progress still reflects the furthest viewer.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.event import InvitationStatus, MKEvent, MKEventInvitation
from services.portal.mk_events_utils import is_event_terminated


class PresenceError(Exception):
    """Service-level error with an HTTP status code."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def _locked_membership(
    db: AsyncSession, event_id: int, user_id: int,
) -> tuple[MKEvent, MKEventInvitation]:
    """Fetch ``(event, invitation)`` under row locks, raising if either
    is missing, the event is terminated, or the membership is not in
    ``accepted`` status. Callers must commit / rollback themselves."""
    event = (await db.execute(
        select(MKEvent)
        .where(MKEvent.id == event_id)
        .with_for_update()
    )).scalar_one_or_none()
    if not event:
        await db.rollback()
        raise PresenceError(404, "not_found")
    if is_event_terminated(event):
        await db.rollback()
        raise PresenceError(410, "event_ended")
    inv = (await db.execute(
        select(MKEventInvitation)
        .where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == user_id,
            MKEventInvitation.status == InvitationStatus.ACCEPTED.value,
        )
        .with_for_update()
    )).scalar_one_or_none()
    if not inv:
        await db.rollback()
        raise PresenceError(403, "not_member")
    return event, inv


async def heartbeat(
    db: AsyncSession, event_id: int, user_id: int,
) -> dict:
    """Stamp the viewer's ``last_seen_at`` to the current UTC instant."""
    _, inv = await _locked_membership(db, event_id, user_id)
    inv.last_seen_at = datetime.now(timezone.utc)
    db.add(inv)
    await db.commit()
    return {"ok": True}


async def leave_room(
    db: AsyncSession, event_id: int, user_id: int,
) -> dict:
    """Clear ``last_seen_at`` so peers stop seeing the seated avatar.

    The seat itself (``seat_index``) is preserved so a returning
    viewer takes back the same seat — only the live presence flag
    drops, not the assignment.
    """
    _, inv = await _locked_membership(db, event_id, user_id)
    inv.last_seen_at = None
    db.add(inv)
    await db.commit()
    return {"ok": True}


async def advance_self_step(
    db: AsyncSession, event_id: int, user_id: int,
) -> dict:
    """Bump the viewer's own ``user_step`` and re-sync the event-wide max.

    The cinema room runs a per-user marathon progression so a viewer
    who finishes film 1 can move on without waiting for the latecomers.
    ``MKEvent.current_step`` is kept in sync with the furthest viewer
    (``max(user_step)`` across accepted, seated invitations) so the
    group-wide signals (e.g. the "Marathon · film X/Y" header) reflect
    the leader's progress.
    """
    event, inv = await _locked_membership(db, event_id, user_id)
    items = list(event.tmdb_ids or [])
    if len(items) <= 1:
        await db.rollback()
        raise PresenceError(400, "not_a_marathon")
    if inv.user_step >= len(items) - 1:
        await db.rollback()
        raise PresenceError(400, "already_last")
    inv.user_step = inv.user_step + 1
    db.add(inv)
    max_step = (await db.execute(
        select(func.max(MKEventInvitation.user_step)).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == InvitationStatus.ACCEPTED.value,
            MKEventInvitation.seat_index.isnot(None),
        )
    )).scalar() or 0
    new_event_step = min(int(max_step), len(items) - 1)
    if event.current_step != new_event_step:
        event.current_step = new_event_step
        db.add(event)
    await db.commit()
    return {
        "ok": True,
        "user_step": inv.user_step,
        "current_step": event.current_step,
    }
