"""Shared helpers for the MediaKeeper Events layer: constants, user label
resolver, event serializer, scheduling-conflict check."""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.event import EventStatus, InvitationStatus, MKEvent, MKEventInvitation
from models.portal.profile import UserProfile
from services.portal._rank_tiers import tier_for_level
from services.portal.avatars import avatar_public_url

logger = logging.getLogger("mediakeeper.portal.mk_events")

MAX_INVITE_RETRIES = 3
# Hard ceiling for per-event capacity. Picks the upper bound of the
# admin-tunable range (``portal.events.max_participants_max``) so the
# legacy seat-allocation tests keep working without an admin row.
# Used as a clamp when ``event.max_participants`` is out of bounds —
# never as a default for the cinema layout.
MAX_PARTICIPANTS = 20
ROOM_OPEN_BEFORE_MIN = 15
# Hard time-based cutoff so an event that nobody marked ``done`` can't
# stay "live" forever — the cinema room closes that many hours past
# ``scheduled_at``, even for marathons. Covers a single movie or a short
# back-to-back screening; longer events can still be re-opened by an
# admin via the explicit ``done`` status reset (out of scope here).
ROOM_CLOSE_AFTER_HOURS = 6
# Live presence in the cinema room: a viewer is considered ``online``
# when the front-end has heart-beat them within this window. Past it,
# the seat avatar disappears from peers' view even though the seat
# stays reserved (see ``MKEventInvitation.last_seen_at``). The poller
# runs every 3 s and the heartbeat every 5 s, so a 15 s grace window
# tolerates one missed beat without flapping.
PRESENCE_WINDOW_SECONDS = 15


def is_currently_in_room(
    last_seen_at: datetime | None, now: datetime | None = None,
) -> bool:
    """True when the viewer has heart-beat within the presence window.

    Mirrors ``is_event_terminated`` tzinfo handling so the same payload
    works against PostgreSQL (tz-aware) and SQLite (the test engine
    strips ``tzinfo``).
    """
    if last_seen_at is None:
        return False
    reference = now or datetime.now(timezone.utc)
    stamped = last_seen_at
    if stamped.tzinfo is None and reference.tzinfo is not None:
        stamped = stamped.replace(tzinfo=timezone.utc)
    elif stamped.tzinfo is not None and reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return (reference - stamped) <= timedelta(seconds=PRESENCE_WINDOW_SECONDS)


def is_event_terminated(event: MKEvent, now: datetime | None = None) -> bool:
    """True when the event no longer accepts room entries or accepts.

    The function is purely time / status driven so it stays cheap to
    evaluate on every list serialisation. Three terminal signals:

    - ``status == "cancelled"`` — explicit creator cancellation.
    - ``status == "done"`` — explicit marker (unset in production today,
      but reserved for the future "everyone left" cleanup job).
    - ``now > scheduled_at + ROOM_CLOSE_AFTER_HOURS`` — soft cutoff so
      stale events drop out of the live UI without manual housekeeping.
    """
    if event.status in (EventStatus.CANCELLED.value, EventStatus.DONE.value):
        return True
    if not event.scheduled_at:
        return False
    reference = now or datetime.now(timezone.utc)
    scheduled = event.scheduled_at
    # Normalise tzinfo on both sides: SQLite (test engine) strips it
    # whereas PostgreSQL preserves it, and the surrounding callers may
    # pass either a tz-aware or a tz-naive ``now`` (the atomicity tests
    # monkey-patch ``datetime.now`` to return naive UTC values).
    if scheduled.tzinfo is None and reference.tzinfo is not None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    elif scheduled.tzinfo is not None and reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return reference > scheduled + timedelta(hours=ROOM_CLOSE_AFTER_HOURS)


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
        select(
            MKEventInvitation,
            User.username,
            UserProfile.display_name,
            UserProfile.avatar_url,
            UserProfile.avatar_custom_path,
            UserProfile.level,
        )
        .join(User, User.id == MKEventInvitation.user_id, isouter=True)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(MKEventInvitation.event_id == event.id)
    )).all()
    invitations = []
    now = datetime.now(timezone.utc)
    for inv, username, display, emby_avatar, custom_avatar_path, level in inv_rows:
        # Custom uploads take precedence over the Emby-proxied URL — same
        # rule the profile serializer applies. The seats UI falls back to
        # the username initial when both are missing (purged user, fresh
        # account with no profile, etc.).
        avatar = avatar_public_url(custom_avatar_path) if custom_avatar_path else emby_avatar
        eff_level = level or 1
        invitations.append({
            "id": inv.id,
            "user_id": inv.user_id,
            "username": display or username or f"user#{inv.user_id}",
            "avatar_url": avatar,
            "level": eff_level,
            "tier": tier_for_level(eff_level),
            "status": inv.status,
            "invite_count": inv.invite_count,
            "seat_index": inv.seat_index,
            # Per-user marathon step (see migration 051). Drives the
            # launch CTA + the "X/Y" cell in the marathon panel so
            # latecomers can stay on their film while peers advance.
            "user_step": inv.user_step,
            # Live presence flag for the seats UI — the seat row is
            # kept (returning viewer takes back the same seat) but
            # the avatar fades out once the heartbeat lapses.
            "last_seen_at": inv.last_seen_at.isoformat() if inv.last_seen_at else None,
            "is_currently_in_room": is_currently_in_room(inv.last_seen_at, now),
            "responded_at": inv.responded_at.isoformat() if inv.responded_at else None,
        })

    creator_label = await _user_label(db, event.creator_user_id)

    accepted_count = sum(1 for i in invitations if i["status"] == InvitationStatus.ACCEPTED.value)
    max_p = int(event.max_participants or 0)
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
        # Composite flag the front-end uses to gray out the join / accept
        # buttons and surface a "Terminated" pill so users don't dive into
        # a dead cinema room. Mirrors ``is_event_terminated``.
        "is_terminated": is_event_terminated(event),
        "room_opened_at": event.room_opened_at.isoformat() if event.room_opened_at else None,
        "current_step": event.current_step,
        # Per-event capacity surface so the front-end can render the
        # right grid (5/10/15/20 seats) and a "Complet" pill on public
        # event cards once ``accepted_count >= max_participants``.
        "max_participants": max_p,
        "accepted_count": accepted_count,
        "is_full": max_p > 0 and accepted_count >= max_p,
        "invitations": invitations,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None,
    }


async def _count_seated(db: AsyncSession, event_id: int) -> int:
    """Return how many accepted invitations currently hold a seat.

    Used by ``enter_room`` to assign the next sequential ``seat_index``
    (0..N-1) so the cinema layout never has gaps — the front-end picks
    a centred grid position from that index.
    """
    return int((await db.execute(
        select(func.count(MKEventInvitation.id)).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == InvitationStatus.ACCEPTED.value,
            MKEventInvitation.seat_index.isnot(None),
        )
    )).scalar() or 0)


async def _compact_seats(db: AsyncSession, event_id: int) -> None:
    """Reassign ``seat_index`` 0..N-1 to the seated invitations,
    ordered by ``responded_at``.

    Called after a viewer declines or is removed so the remaining
    avatars compact back to the centre of the cinema layout (option B
    rebalance). The locked rows in the surrounding atomic step keep
    this from racing with a concurrent ``enter_room``.
    """
    rows = (await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == InvitationStatus.ACCEPTED.value,
            MKEventInvitation.seat_index.isnot(None),
        ).order_by(MKEventInvitation.responded_at, MKEventInvitation.id)
    )).scalars().all()
    for idx, inv in enumerate(rows):
        if inv.seat_index != idx:
            inv.seat_index = idx
            db.add(inv)


async def _has_conflict(
    db: AsyncSession,
    user_id: int,
    scheduled_at: datetime,
    *,
    exclude_event_id: int | None = None,
) -> bool:
    """
    Approximate overlap check: returns True if the user is already
    accepted on another event whose start time is within ±2h of the
    new one. We don't store durations yet so a fixed window is the
    safest pragmatic approach.

    ``exclude_event_id`` skips a specific row from the count. The
    accept flow uses it to exclude the event being accepted right
    now — the invitation row is flipped to ``accepted`` in the same
    session before the check runs, so the read-your-writes view of
    that session would otherwise treat the event as colliding with
    itself.
    """
    window_start = scheduled_at - timedelta(hours=2)
    window_end = scheduled_at + timedelta(hours=2)
    stmt = (
        select(func.count(MKEvent.id))
        .join(MKEventInvitation, MKEventInvitation.event_id == MKEvent.id)
        .where(
            MKEventInvitation.user_id == user_id,
            MKEventInvitation.status == InvitationStatus.ACCEPTED.value,
            MKEvent.status == EventStatus.SCHEDULED.value,
            MKEvent.scheduled_at >= window_start,
            MKEvent.scheduled_at <= window_end,
        )
    )
    if exclude_event_id is not None:
        stmt = stmt.where(MKEvent.id != exclude_event_id)
    res = await db.execute(stmt)
    return int(res.scalar() or 0) > 0
