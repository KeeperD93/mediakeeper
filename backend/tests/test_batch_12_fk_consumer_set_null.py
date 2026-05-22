"""Verify the consumer-side FKs to ``users.id`` flip to ``SET NULL``
on a hard delete.

Eight tables hold content that must outlive the GDPR purge of its
author:

* ``news.author_id``
* ``mk_event_messages.user_id``
* ``watch_parties.host_user_id``
* ``chat_reports.reporter_id``
* ``ticket_replies.user_id``
* ``tickets.user_id``
* ``media_requests.user_id``
* ``mk_events.creator_user_id``

The FK rules come from the SQLAlchemy models (mirrored by Alembic
migration 041). The tests use ``Base.metadata.create_all`` which reads
the model metadata, so the SET NULL is exercised end-to-end without
running the migration. SQLite FK enforcement is enabled by the test
conftest pragma.

Three additional tests cover:

* the GDPR purge auto-cancels every still-``scheduled`` ``mk_event``
  before the FK SET NULL fires (no zombies),
* ``update_ticket_status`` skips the bell when the author is gone,
* ``update_request_status`` skips the bell when the requester is gone.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.portal.chat import ChatMessage, ChatReport, ChatRoom
from models.portal.event import (
    EventStatus, MKEvent, MKEventMessage, MKNotification,
    WatchParty,
)
from models.portal.news import News
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.portal.ticket import Ticket, TicketReply
from models.user import User
from services.portal import requests as requests_svc
from services.portal import tickets as tickets_svc
from services.portal.gdpr import purge_pending_deletions
from services.settings import set_setting


# ─────────────────────────── helpers ───────────────────────────


async def _make_user(db_session, *, username: str) -> User:
    user = User(username=username, hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(UserProfile(
        user_id=user.id, display_name=username, role="viewer",
    ))
    await db_session.commit()
    return user


async def _expire_and_get(db_session, model, primary_key):
    """Re-read a row from the DB so the post-cascade value is visible.

    SQLAlchemy keeps the in-memory row in the identity map; expiring
    forces a SELECT that picks up the FK ``SET NULL`` mutation.
    """
    instance = await db_session.get(model, primary_key)
    if instance is None:
        return None
    db_session.expire(instance)
    return await db_session.get(model, primary_key)


# ─────────────────────────── per-table SET NULL ───────────────────────────


@pytest.mark.asyncio
async def test_news_author_id_set_null_on_user_delete(db_session):
    user = await _make_user(db_session, username="news-author")
    article = News(
        author_id=user.id,
        title="Library refresh",
        content="<p>New titles landed.</p>",
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)
    article_id = article.id

    await db_session.delete(user)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, News, article_id)
    assert survivor is not None
    assert survivor.author_id is None
    assert survivor.title == "Library refresh"


@pytest.mark.asyncio
async def test_mk_event_messages_user_id_set_null_on_user_delete(db_session):
    creator = await _make_user(db_session, username="evt-creator")
    speaker = await _make_user(db_session, username="evt-speaker")
    event = MKEvent(
        creator_user_id=creator.id,
        title="Movie night",
        kind="private",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "T"}],
        scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
        status=EventStatus.DONE.value,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    msg = MKEventMessage(
        event_id=event.id, user_id=speaker.id, content="hi",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)
    msg_id = msg.id

    await db_session.delete(speaker)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, MKEventMessage, msg_id)
    assert survivor is not None
    assert survivor.user_id is None
    assert survivor.content == "hi"


@pytest.mark.asyncio
async def test_watch_parties_host_user_id_set_null_on_user_delete(db_session):
    host = await _make_user(db_session, username="party-host")
    party = WatchParty(
        host_user_id=host.id,
        title="Saturday screening",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add(party)
    await db_session.commit()
    await db_session.refresh(party)
    party_id = party.id

    await db_session.delete(host)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, WatchParty, party_id)
    assert survivor is not None
    assert survivor.host_user_id is None
    assert survivor.title == "Saturday screening"


@pytest.mark.asyncio
async def test_chat_reports_reporter_id_set_null_on_user_delete(db_session):
    author = await _make_user(db_session, username="chat-author")
    reporter = await _make_user(db_session, username="chat-reporter")
    room = ChatRoom(type="lounge", name="lounge")
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)
    msg = ChatMessage(room_id=room.id, user_id=author.id, content="hello")
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)
    report = ChatReport(
        message_id=msg.id, reporter_id=reporter.id, reason="spam",
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    report_id = report.id

    await db_session.delete(reporter)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, ChatReport, report_id)
    assert survivor is not None
    assert survivor.reporter_id is None
    assert survivor.reason == "spam"


@pytest.mark.asyncio
async def test_ticket_replies_user_id_set_null_on_user_delete(db_session):
    owner = await _make_user(db_session, username="ticket-owner")
    replier = await _make_user(db_session, username="ticket-replier")
    ticket = Ticket(
        user_id=owner.id,
        media_title="Movie X",
        media_type="movie",
        emby_item_id="emby-1",
        issue_type="audio",
        description="Audio drift",
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    reply = TicketReply(
        ticket_id=ticket.id, user_id=replier.id, content="thanks",
    )
    db_session.add(reply)
    await db_session.commit()
    await db_session.refresh(reply)
    reply_id = reply.id

    await db_session.delete(replier)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, TicketReply, reply_id)
    assert survivor is not None
    assert survivor.user_id is None
    assert survivor.content == "thanks"


@pytest.mark.asyncio
async def test_tickets_user_id_set_null_on_user_delete(db_session):
    owner = await _make_user(db_session, username="ticket-only-owner")
    ticket = Ticket(
        user_id=owner.id,
        media_title="Movie Y",
        media_type="movie",
        emby_item_id="emby-2",
        issue_type="subtitles",
        description="Missing subs",
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    ticket_id = ticket.id

    await db_session.delete(owner)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, Ticket, ticket_id)
    assert survivor is not None
    assert survivor.user_id is None
    assert survivor.media_title == "Movie Y"


@pytest.mark.asyncio
async def test_media_requests_user_id_set_null_on_user_delete(db_session):
    requester = await _make_user(db_session, username="media-requester")
    req = MediaRequest(
        user_id=requester.id,
        tmdb_id=42,
        media_type="movie",
        title="Inception",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)
    req_id = req.id

    await db_session.delete(requester)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, MediaRequest, req_id)
    assert survivor is not None
    assert survivor.user_id is None
    assert survivor.title == "Inception"


@pytest.mark.asyncio
async def test_mk_events_creator_user_id_set_null_on_user_delete(db_session):
    """Past events (``status='done'``) keep their row + lose the creator
    link. The auto-cancel branch only kicks in for ``scheduled`` events,
    covered separately below."""
    creator = await _make_user(db_session, username="evt-past-creator")
    event = MKEvent(
        creator_user_id=creator.id,
        title="Last week",
        kind="private",
        tmdb_ids=[{"tmdb_id": 7, "media_type": "movie", "title": "Old"}],
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=2),
        status=EventStatus.DONE.value,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    event_id = event.id

    await db_session.delete(creator)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, MKEvent, event_id)
    assert survivor is not None
    assert survivor.creator_user_id is None
    assert survivor.title == "Last week"


# ─────────────────────────── auto-cancel of scheduled mk_events ─────


@pytest.mark.asyncio
async def test_purge_auto_cancels_scheduled_mk_events_of_purged_user(db_session):
    """A scheduled event whose creator is being purged is moved to
    ``cancelled`` *before* the FK SET NULL kicks in, so it doesn't
    become a zombie that nobody can edit."""
    await set_setting(db_session, "gdpr.enabled", "true")
    creator = await _make_user(db_session, username="scheduled-creator")
    creator.pending_deletion_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add(creator)
    await db_session.commit()
    creator_id = creator.id

    event = MKEvent(
        creator_user_id=creator_id,
        title="Future",
        kind="private",
        tmdb_ids=[{"tmdb_id": 9, "media_type": "movie", "title": "F"}],
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=EventStatus.SCHEDULED.value,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    event_id = event.id

    purged = await purge_pending_deletions(db_session)
    assert purged == 1

    survivor = await _expire_and_get(db_session, MKEvent, event_id)
    assert survivor is not None
    # The auto-cancel ran before the user delete, so the row carries
    # ``cancelled`` *and* the FK has been cleared by SET NULL.
    assert survivor.status == EventStatus.CANCELLED.value
    assert survivor.creator_user_id is None
    # The owning ``users`` row is gone for good.
    assert (await db_session.execute(
        select(User).where(User.id == creator_id)
    )).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_purge_does_not_touch_done_or_cancelled_mk_events(db_session):
    """Only ``scheduled`` events are auto-cancelled — the historical
    record (``done``, ``cancelled``) is left intact, anonymised through
    SET NULL."""
    await set_setting(db_session, "gdpr.enabled", "true")
    creator = await _make_user(db_session, username="done-creator")
    creator.pending_deletion_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add(creator)
    await db_session.commit()

    done = MKEvent(
        creator_user_id=creator.id,
        title="Done",
        kind="private",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "D"}],
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=1),
        status=EventStatus.DONE.value,
    )
    cancelled = MKEvent(
        creator_user_id=creator.id,
        title="Cancelled",
        kind="private",
        tmdb_ids=[{"tmdb_id": 2, "media_type": "movie", "title": "C"}],
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=1),
        status=EventStatus.CANCELLED.value,
    )
    db_session.add_all([done, cancelled])
    await db_session.commit()
    await db_session.refresh(done)
    await db_session.refresh(cancelled)
    done_id, cancelled_id = done.id, cancelled.id

    await purge_pending_deletions(db_session)

    survivor_done = await _expire_and_get(db_session, MKEvent, done_id)
    survivor_cancelled = await _expire_and_get(db_session, MKEvent, cancelled_id)
    assert survivor_done.status == EventStatus.DONE.value
    assert survivor_done.creator_user_id is None
    assert survivor_cancelled.status == EventStatus.CANCELLED.value
    assert survivor_cancelled.creator_user_id is None


# ─────────────────────────── notif guards ───────────────────────────


@pytest.mark.asyncio
async def test_update_ticket_status_skips_notif_when_author_purged(db_session):
    """``update_ticket_status`` must not raise when the author has been
    purged (FK ``user_id`` cleared) — the bell would otherwise try to
    insert into ``mk_notifications`` with a NULL user id."""
    owner = await _make_user(db_session, username="ticket-purged")
    ticket = Ticket(
        user_id=owner.id,
        media_title="Movie Z",
        media_type="movie",
        emby_item_id="emby-9",
        issue_type="audio",
        description="Audio drift",
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    ticket_id = ticket.id

    await db_session.delete(owner)
    await db_session.commit()

    # Sanity check — the FK cleared, but the ticket survives.
    survivor = await _expire_and_get(db_session, Ticket, ticket_id)
    assert survivor.user_id is None

    with patch(
        "services.portal.notifications.create",
        new=AsyncMock(return_value={"success": True}),
    ) as mock_create:
        result = await tickets_svc.update_ticket_status(
            db_session, ticket_id, "resolved",
        )

    assert result == {"success": True}
    mock_create.assert_not_awaited()
    # Confirm no orphan notification reached the table either.
    rows = (await db_session.execute(
        select(MKNotification).where(MKNotification.type == "ticket_resolved")
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_update_request_status_skips_notif_when_requester_purged(db_session):
    """Same guarantee on the media-request side: an admin can still
    flip a request to approved/available even if the requester is
    gone, without the bell crashing."""
    requester = await _make_user(db_session, username="req-purged")
    admin = await _make_user(db_session, username="req-admin")
    req = MediaRequest(
        user_id=requester.id,
        tmdb_id=99,
        media_type="movie",
        title="Some title",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)
    req_id = req.id

    await db_session.delete(requester)
    await db_session.commit()

    survivor = await _expire_and_get(db_session, MediaRequest, req_id)
    assert survivor.user_id is None

    with patch(
        "services.portal.notifications.create",
        new=AsyncMock(return_value={"success": True}),
    ) as mock_create:
        result = await requests_svc.update_request_status(
            db_session, req_id, "approved", admin.id,
        )

    assert result["success"] is True
    mock_create.assert_not_awaited()


# ─────────────────────────── serializer null-safety ─────────────────


@pytest.mark.asyncio
async def test_get_ticket_serializer_marks_requester_as_deleted(db_session):
    """``get_ticket`` must surface ``requester_deleted=True`` so the
    frontend renders the localised placeholder instead of a blank
    avatar."""
    owner = await _make_user(db_session, username="ticket-anon")
    ticket = Ticket(
        user_id=owner.id,
        media_title="Movie A",
        media_type="movie",
        emby_item_id="emby-z",
        issue_type="audio",
        description="Drift",
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    ticket_id = ticket.id

    await db_session.delete(owner)
    await db_session.commit()
    # Expire the identity-map cache so ``get_ticket`` re-reads the
    # post-cascade ``user_id IS NULL`` from the database instead of the
    # stale instance kept in this session.
    db_session.expire_all()

    payload = await tickets_svc.get_ticket(db_session, ticket_id)
    assert payload is not None
    assert payload["user_id"] is None
    assert payload["requester"] is None
    assert payload["requester_deleted"] is True
