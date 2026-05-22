"""Self-collision regression for the event-accept conflict warning.

Before this fix, ``respond(decision="accept")`` flipped the invitation
row to ``accepted`` and then ran ``_has_conflict`` in the same session
— the read-your-writes view of that session counted the event being
accepted as a colliding row, so the API answered ``conflict: true`` to
every accept, and the overlay surfaced a warning on the same event the
user had just joined.

Two coverage points:

1. Accepting an invitation on a single event returns ``conflict: false``
   (no self-collision).
2. Accepting a second event scheduled within ±2h of an already-accepted
   one still returns ``conflict: true`` — the exclude filter must not
   silence a real overlap.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.security import hash_password
from models.portal.event import (
    EventStatus,
    InvitationStatus,
    MKEvent,
    MKEventInvitation,
)
from models.portal.profile import UserProfile
from models.user import User
from services.portal.mk_events_members import invite_user, respond
from services.portal.mk_events_utils import MAX_PARTICIPANTS


async def _make_user(db, *, username: str) -> User:
    user = User(
        username=username,
        hashed_password=hash_password("MKEventConflictTestPwd123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
    )
    db.add(profile)
    await db.commit()
    return user


async def _make_event(
    db,
    *,
    creator: User,
    scheduled_in_minutes: int = 60,
    title: str = "Movie Night",
) -> MKEvent:
    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=scheduled_in_minutes)
    event = MKEvent(
        creator_user_id=creator.id,
        title=title,
        kind="private",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": title}],
        scheduled_at=scheduled_at,
        status=EventStatus.SCHEDULED.value,
        max_participants=MAX_PARTICIPANTS,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@pytest.mark.asyncio
async def test_accepting_single_event_does_not_self_collide(db_session):
    """A user accepting an event has no other accepted event in the
    ±2h window, so the warning must not fire."""
    creator = await _make_user(db_session, username="conflict-creator")
    invitee = await _make_user(db_session, username="conflict-invitee")
    event = await _make_event(db_session, creator=creator)

    invite_res = await invite_user(db_session, event.id, creator.id, invitee.id)
    assert invite_res.get("ok") is True, invite_res

    accept_res = await respond(db_session, event.id, invitee.id, "accept")
    assert accept_res.get("ok") is True, accept_res
    assert accept_res.get("conflict") is False, (
        "accepting an event must not self-trigger the conflict warning; "
        f"got {accept_res!r}"
    )


@pytest.mark.asyncio
async def test_accepting_second_overlapping_event_does_collide(db_session):
    """A genuinely overlapping second event must still raise the
    warning — the exclude filter only suppresses self-collisions."""
    creator = await _make_user(db_session, username="overlap-creator")
    invitee = await _make_user(db_session, username="overlap-invitee")

    # First event — already accepted via a pre-seeded invitation row.
    first = await _make_event(
        db_session,
        creator=creator,
        scheduled_in_minutes=60,
        title="First show",
    )
    db_session.add(
        MKEventInvitation(
            event_id=first.id,
            user_id=invitee.id,
            status=InvitationStatus.ACCEPTED.value,
            invite_count=1,
        )
    )
    await db_session.commit()

    # Second event scheduled inside the ±2h window of the first.
    second = await _make_event(
        db_session,
        creator=creator,
        scheduled_in_minutes=90,
        title="Second show",
    )
    invite_res = await invite_user(db_session, second.id, creator.id, invitee.id)
    assert invite_res.get("ok") is True, invite_res

    accept_res = await respond(db_session, second.id, invitee.id, "accept")
    assert accept_res.get("ok") is True, accept_res
    assert accept_res.get("conflict") is True, (
        "two events within ±2h must still raise the conflict warning; "
        f"got {accept_res!r}"
    )
