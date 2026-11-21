"""The « For you » block of the daily digest, and the events it keeps."""
from datetime import UTC, datetime, timedelta

import pytest

from constants.daily_digest import (
    FOR_YOU_LIMIT,
    FOR_YOU_REQUEST_APPROVED,
    FOR_YOU_REQUEST_AVAILABLE,
    FOR_YOU_TICKET_REPLY,
)
from constants.requests import (
    REQUEST_APPROVED,
    REQUEST_AVAILABLE,
    REQUEST_PENDING,
    REQUEST_REJECTED,
)
from models.portal.event import (
    EventStatus,
    InvitationStatus,
    MKEvent,
    MKEventInvitation,
)
from models.portal.request import MediaRequest
from models.portal.ticket import Ticket, TicketReply
from services.portal import daily_digest_for_you as for_you
from services.portal import daily_digest_sources as sources
from tests._portal_profile_helpers import make_portal_user

NOW = datetime.now(UTC)
SINCE = NOW - timedelta(days=10)


def _request(user_id: int, status: str, at: datetime, title: str = "Test Movie") -> MediaRequest:
    return MediaRequest(
        user_id=user_id, tmdb_id=12345, media_type="movie", title=title, status=status,
        available_at=at if status == REQUEST_AVAILABLE else None, updated_at=at,
    )


def _ticket(user_id: int, title: str = "Test Movie") -> Ticket:
    return Ticket(
        user_id=user_id, media_title=title, media_type="movie",
        issue_type="video", description="Test issue",
    )


def _reply(ticket: Ticket, user_id: int | None, at: datetime) -> TicketReply:
    return TicketReply(ticket_id=ticket.id, user_id=user_id, content="Test reply", created_at=at)


async def _seed_tickets(db, alice_id: int, admin_id: int) -> tuple[Ticket, ...]:
    answered, own_only, too_old, purged = (_ticket(alice_id, f"Ticket {n}") for n in range(4))
    db.add_all([answered, own_only, too_old, purged, _ticket(admin_id, "Someone else")])
    await db.flush()
    db.add_all([
        _reply(answered, admin_id, NOW - timedelta(hours=3)),
        _reply(answered, alice_id, NOW - timedelta(hours=1)),  # her own answer is no news
        _reply(own_only, alice_id, NOW - timedelta(hours=1)),
        _reply(too_old, admin_id, SINCE - timedelta(minutes=1)),
        _reply(purged, None, NOW - timedelta(days=2)),
    ])
    await db.commit()
    return answered, purged


@pytest.mark.asyncio
async def test_for_you_lists_each_kind_newest_first(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    admin, _ = await make_portal_user(db_session, username="admin_test", role="admin")
    db_session.add_all([
        _request(alice.id, REQUEST_AVAILABLE, NOW - timedelta(days=1), "Available Movie"),
        _request(alice.id, REQUEST_APPROVED, NOW - timedelta(hours=2), "Approved Movie"),
        _request(alice.id, REQUEST_PENDING, NOW - timedelta(hours=1)),
        _request(alice.id, REQUEST_REJECTED, NOW - timedelta(hours=1)),
        _request(alice.id, REQUEST_AVAILABLE, SINCE - timedelta(minutes=1)),
        _request(admin.id, REQUEST_AVAILABLE, NOW - timedelta(hours=1)),
    ])
    answered, purged = await _seed_tickets(db_session, alice.id, admin.id)

    items = await for_you.recent(db_session, alice.id, since=SINCE)

    assert [(item["kind"], item["title"]) for item in items] == [
        (FOR_YOU_REQUEST_APPROVED, "Approved Movie"),
        (FOR_YOU_TICKET_REPLY, "Ticket 0"),
        (FOR_YOU_REQUEST_AVAILABLE, "Available Movie"),
        (FOR_YOU_TICKET_REPLY, "Ticket 3"),
    ]
    approved, reply, available, purged_reply = items
    assert approved | {"at": None} == {
        "kind": FOR_YOU_REQUEST_APPROVED, "title": "Approved Movie", "at": None,
        "tmdb_id": 12345, "media_type": "movie", "ticket_id": None,
    }
    # The ticket is dated by the last answer of someone else, not by her own.
    assert datetime.fromisoformat(reply["at"]) == NOW - timedelta(hours=3)
    assert (reply["ticket_id"], reply["tmdb_id"], reply["media_type"]) == (answered.id, None, None)
    assert datetime.fromisoformat(available["at"]) == NOW - timedelta(days=1)
    assert purged_reply["ticket_id"] == purged.id


@pytest.mark.asyncio
async def test_for_you_keeps_the_five_newest(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    db_session.add_all(
        _request(alice.id, REQUEST_AVAILABLE, NOW - timedelta(hours=hours), f"Movie {hours}")
        for hours in range(1, 8)
    )
    await db_session.commit()

    items = await for_you.recent(db_session, alice.id, since=SINCE)

    assert len(items) == FOR_YOU_LIMIT
    assert [item["title"] for item in items] == [f"Movie {hours}" for hours in range(1, 6)]


@pytest.mark.asyncio
async def test_for_you_starts_at_the_given_watermark(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    db_session.add(_request(alice.id, REQUEST_AVAILABLE, NOW - timedelta(hours=5)))
    await db_session.commit()

    assert await for_you.recent(db_session, alice.id, since=NOW - timedelta(hours=4)) == []
    assert len(await for_you.recent(db_session, alice.id, since=NOW - timedelta(hours=6))) == 1


def _event(creator_id: int, title: str, kind: str = "private", status: str = EventStatus.SCHEDULED.value):
    return MKEvent(
        creator_user_id=creator_id, title=title, kind=kind, status=status,
        tmdb_ids=[{"tmdb_id": 12345, "media_type": "movie", "title": "Test Movie"}],
        scheduled_at=NOW + timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_events_leave_out_the_cancelled_and_the_declined(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    host, _ = await make_portal_user(db_session, username="host")
    invited = {
        "Invited": InvitationStatus.PENDING.value,
        "Declined": InvitationStatus.DECLINED.value,
        "Removed": InvitationStatus.REMOVED.value,
        "Public declined": InvitationStatus.DECLINED.value,
    }
    events = {title: _event(host.id, title, kind="public" if "Public" in title else "private")
              for title in invited}
    events["Cancelled"] = _event(host.id, "Cancelled", status=EventStatus.CANCELLED.value)
    events["Open public"] = _event(host.id, "Open public", kind="public")
    db_session.add_all(events.values())
    await db_session.flush()
    invited["Cancelled"] = InvitationStatus.ACCEPTED.value
    db_session.add_all(
        MKEventInvitation(event_id=events[title].id, user_id=alice.id, status=status)
        for title, status in invited.items()
    )
    await db_session.commit()

    titles = [event["title"] for event in await sources.upcoming_events(db_session, alice.id)]

    assert sorted(titles) == ["Invited", "Open public"]
