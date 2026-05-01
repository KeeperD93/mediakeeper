"""Event CRUD — create, update, cancel, list, get one."""
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.event import MKEvent, MKEventInvitation
from services.portal import notifications as notifs
from services.portal.mk_events_utils import (
    MAX_PARTICIPANTS, _user_label, _serialize_event,
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
) -> dict:
    """
    Create a new event. For private events, `invitees` is the list of
    user_ids to invite. For public events, `invitees` is ignored and
    we broadcast a notification to every Portal user.
    """
    if kind not in ("private", "public"):
        return {"error": "invalid_kind"}
    if not title.strip():
        return {"error": "title_required"}
    if not tmdb_ids:
        return {"error": "no_media"}
    if scheduled_at <= datetime.now(timezone.utc):
        return {"error": "scheduled_in_past"}

    invitees = invitees or []
    if kind == "private" and len(invitees) >= MAX_PARTICIPANTS:
        return {"error": "too_many_invitees"}

    event = MKEvent(
        creator_user_id=creator_user_id,
        title=title.strip(),
        kind=kind,
        tmdb_ids=tmdb_ids,
        scheduled_at=scheduled_at,
        comment=(comment or "").strip() or None,
        status="scheduled",
    )
    db.add(event)
    await db.flush()

    # Creator is implheretly accepted.
    creator_inv = MKEventInvitation(
        event_id=event.id,
        user_id=creator_user_id,
        status="accepted",
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
            db.add(MKEventInvitation(
                event_id=event.id,
                user_id=uid,
                status="pending",
                invite_count=1,
            ))
            await notifs.create(db, uid, "event_invitation", payload_base)
    else:
        # Public: notify everyone except the creator.
        users = (await db.execute(
            select(User.id).where(User.id != creator_user_id)
        )).scalars().all()
        await notifs.create_many(db, list(users), "event_invitation", payload_base)

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
    if event.status != "scheduled":
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
            MKEventInvitation.status == "accepted",
            MKEventInvitation.user_id != creator_user_id,
        )
    )).scalars().all()
    payload = {
        "event_id": event.id,
        "title": event.title,
        "scheduled_at": event.scheduled_at.isoformat(),
    }
    await notifs.create_many(db, list(accepted), "event_modified", payload)

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
    if event.status != "scheduled":
        return {"error": "not_cancellable"}

    event.status = "cancelled"
    db.add(event)

    accepted = (await db.execute(
        select(MKEventInvitation.user_id).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == "accepted",
            MKEventInvitation.user_id != creator_user_id,
        )
    )).scalars().all()
    payload = {"event_id": event.id, "title": event.title}
    await notifs.create_many(db, list(accepted), "event_cancelled", payload)
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
                 MKEvent.status == "scheduled"),
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
        .where(MKEvent.status == "scheduled", MKEvent.scheduled_at >= now)
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
                MKEventInvitation.status != "removed",
            )
        )).scalar_one_or_none()
        if not inv:
            return {"error": "forbidden"}
    return await _serialize_event(db, ev)
