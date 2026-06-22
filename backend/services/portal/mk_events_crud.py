"""Event CRUD — create, update, cancel, list, get one."""
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from constants.notifications import (
    NOTIF_EVENT_CANCELLED,
    NOTIF_EVENT_INVITATION,
    NOTIF_EVENT_MODIFIED,
)
from models.user import User
from models.portal.event import (
    EventStatus,
    InvitationStatus,
    MKEvent,
    MKEventInvitation,
)
from services.portal import notifications as notifs
from services.portal.admin import (
    PORTAL_EVENT_CAPACITY_STEP,
    get_event_capacity_bounds,
)
from services.portal.mk_events_utils import (
    _user_label, _serialize_event, is_invitable,
)


async def create_event(
    db: AsyncSession,
    creator_user_id: int,
    *,
    title: str,
    kind: str,
    tmdb_ids: list[dict],
    scheduled_at: datetime,
    comment: str | None,
    invitees: list[int] | None = None,
    max_participants: int | None = None,
) -> dict:
    """
    Create a new event. For private events, `invitees` is the list of
    user_ids to invite. For public events, `invitees` is ignored and
    we broadcast a notification to every Portal user.

    ``max_participants`` must be a step-5 multiple within the
    admin-tunable bounds. ``None`` is rejected to keep the create-form
    contract explicit — the Pydantic layer already enforces this for
    the public API, the kwarg fallback here covers callers that pass
    the field through ``**kwargs``.
    """
    if kind not in ("private", "public"):
        return {"error": "invalid_kind"}
    if not title.strip():
        return {"error": "title_required"}
    if not tmdb_ids:
        return {"error": "no_media"}
    if scheduled_at <= datetime.now(timezone.utc):
        return {"error": "scheduled_in_past"}

    min_cap, max_cap = await get_event_capacity_bounds(db)
    if max_participants is None:
        return {"error": "max_participants_required"}
    if max_participants % PORTAL_EVENT_CAPACITY_STEP != 0:
        return {"error": "max_participants_step_violation"}
    if not (min_cap <= max_participants <= max_cap):
        return {"error": "max_participants_out_of_range"}

    invitees = invitees or []
    if kind == "private" and len(invitees) >= max_participants:
        return {"error": "too_many_invitees"}

    event = MKEvent(
        creator_user_id=creator_user_id,
        title=title.strip(),
        kind=kind,
        tmdb_ids=tmdb_ids,
        scheduled_at=scheduled_at,
        comment=(comment or "").strip() or None,
        status=EventStatus.SCHEDULED.value,
        max_participants=max_participants,
    )
    db.add(event)
    await db.flush()

    # Creator is implheretly accepted.
    creator_inv = MKEventInvitation(
        event_id=event.id,
        user_id=creator_user_id,
        status=InvitationStatus.ACCEPTED.value,
        invite_count=1,
        responded_at=datetime.now(timezone.utc),
    )
    db.add(creator_inv)

    creator_label = await _user_label(db, creator_user_id)
    payload_base = {
        "event_id": event.id,
        "title": event.title,
        "kind": event.kind,
        "scheduled_at": event.scheduled_at.isoformat(),
        "from": creator_label,
    }

    if kind == "private":
        invitees = [u for u in set(invitees) if u != creator_user_id]
        for uid in invitees:
            # Never add a private / admin / inactive account as a guest, even
            # if a crafted payload slips a user_id past the picker.
            if not await is_invitable(db, uid):
                continue
            db.add(MKEventInvitation(
                event_id=event.id,
                user_id=uid,
                status=InvitationStatus.PENDING.value,
                invite_count=1,
            ))
            await notifs.create(db, uid, NOTIF_EVENT_INVITATION, payload_base)
    else:
        # Public: notify everyone except the creator.
        users = (await db.execute(
            select(User.id).where(User.id != creator_user_id)
        )).scalars().all()
        await notifs.create_many(db, list(users), NOTIF_EVENT_INVITATION, payload_base)

    await db.commit()
    await db.refresh(event)
    return await _serialize_event(db, event)


async def update_event(
    db: AsyncSession,
    event_id: int,
    creator_user_id: int,
    *,
    title: str | None = None,
    tmdb_ids: list[dict] | None = None,
    scheduled_at: datetime | None = None,
    comment: str | None = None,
) -> dict:
    """
    Edit an event. Only the creator can edit. Notifies every accepted
    invitee so they can opt out if the new conditions don't suit them.
    """
    event = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"error": "not_found"}
    if event.creator_user_id != creator_user_id:
        return {"error": "forbidden"}
    if event.status != EventStatus.SCHEDULED.value:
        return {"error": "not_editable"}

    if title is not None:
        event.title = title.strip()
    if tmdb_ids is not None:
        event.tmdb_ids = tmdb_ids
    if scheduled_at is not None:
        if scheduled_at <= datetime.now(timezone.utc):
            return {"error": "scheduled_in_past"}
        event.scheduled_at = scheduled_at
    if comment is not None:
        event.comment = comment.strip() or None

    db.add(event)

    # Notify every currently-accepted invitee (except the creator).
    accepted = (await db.execute(
        select(MKEventInvitation.user_id).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == InvitationStatus.ACCEPTED.value,
            MKEventInvitation.user_id != creator_user_id,
        )
    )).scalars().all()
    payload = {
        "event_id": event.id,
        "title": event.title,
        "scheduled_at": event.scheduled_at.isoformat(),
    }
    await notifs.create_many(db, list(accepted), NOTIF_EVENT_MODIFIED, payload)

    await db.commit()
    await db.refresh(event)
    return await _serialize_event(db, event)


async def cancel_event(
    db: AsyncSession,
    event_id: int,
    creator_user_id: int,
) -> dict:
    event = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"error": "not_found"}
    if event.creator_user_id != creator_user_id:
        return {"error": "forbidden"}
    if event.status != EventStatus.SCHEDULED.value:
        return {"error": "not_cancellable"}

    event.status = EventStatus.CANCELLED.value
    db.add(event)

    accepted = (await db.execute(
        select(MKEventInvitation.user_id).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == InvitationStatus.ACCEPTED.value,
            MKEventInvitation.user_id != creator_user_id,
        )
    )).scalars().all()
    payload = {"event_id": event.id, "title": event.title}
    await notifs.create_many(db, list(accepted), NOTIF_EVENT_CANCELLED, payload)
    await db.commit()
    return {"ok": True}


async def list_for_user(db: AsyncSession, user_id: int) -> list[dict]:
    """
    Calendar view: every event the user is involved in (created or
    invited) PLUS every public scheduled event in the future, even
    if not yet accepted.
    """
    now = datetime.now(timezone.utc)
    invited_ids = (await db.execute(
        select(MKEventInvitation.event_id).where(
            MKEventInvitation.user_id == user_id,
        )
    )).scalars().all()

    q = select(MKEvent).where(
        or_(
            MKEvent.id.in_(list(invited_ids) or [-1]),
            and_(MKEvent.kind == "public", MKEvent.scheduled_at >= now,
                 MKEvent.status == EventStatus.SCHEDULED.value),
        )
    ).order_by(MKEvent.scheduled_at.asc())
    rows = (await db.execute(q)).scalars().all()
    out: list[dict] = []
    for ev in rows:
        out.append(await _serialize_event(db, ev))
    return out


async def list_upcoming_admin(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Every scheduled future event regardless of privacy — admin view."""
    now = datetime.now(timezone.utc)
    q = (
        select(MKEvent)
        .where(MKEvent.status == EventStatus.SCHEDULED.value, MKEvent.scheduled_at >= now)
        .order_by(MKEvent.scheduled_at.asc())
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    return [await _serialize_event(db, ev) for ev in rows]


async def get_one(db: AsyncSession, event_id: int, user_id: int | None = None) -> dict | None:
    ev = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not ev:
        return None
    if user_id is not None and ev.kind != "public" and ev.creator_user_id != user_id:
        inv = (await db.execute(
            select(MKEventInvitation).where(
                MKEventInvitation.event_id == event_id,
                MKEventInvitation.user_id == user_id,
                MKEventInvitation.status != InvitationStatus.REMOVED.value,
            )
        )).scalar_one_or_none()
        if not inv:
            return {"error": "forbidden"}
    return await _serialize_event(db, ev)
