"""Scheduler-side tests for ``purge_pending_deletions``.

Covers:

* gating (early-return when ``gdpr.enabled`` is ``false``),
* live setting read (toggle changes take effect immediately, no cache),
* time gate (purge only fires past ``pending_deletion_at``),
* chat anonymisation (``user_id`` flips to NULL via the FK SET NULL
  rule applied by migration 040, the message survives).
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models.portal.chat import ChatMessage, ChatRoom
from models.portal.profile import UserProfile
from models.user import User
from services.portal.gdpr import purge_pending_deletions
from services.settings import set_setting


async def _enable_gdpr(db_session) -> None:
    await set_setting(db_session, "gdpr.enabled", "true")


async def _make_user(db_session, *, username: str, pending_at) -> User:
    user = User(username=username, hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    user.deletion_requested_at = pending_at - timedelta(days=30)
    user.pending_deletion_at = pending_at
    db_session.add(user)
    db_session.add(UserProfile(
        user_id=user.id, display_name=username, role="viewer",
    ))
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_purge_returns_zero_when_gdpr_disabled(db_session):
    """Toggle off → no work, even if a user has a lapsed pending date."""
    past = datetime.now(timezone.utc) - timedelta(days=1)
    await _make_user(db_session, username="off-purge", pending_at=past)
    # Setting deliberately not enabled.

    purged = await purge_pending_deletions(db_session)
    assert purged == 0

    still_there = (await db_session.execute(
        select(User).where(User.username == "off-purge")
    )).scalar_one_or_none()
    assert still_there is not None


@pytest.mark.asyncio
async def test_purge_skips_users_whose_grace_period_has_not_lapsed(db_session):
    await _enable_gdpr(db_session)
    future = datetime.now(timezone.utc) + timedelta(days=10)
    await _make_user(db_session, username="future", pending_at=future)

    purged = await purge_pending_deletions(db_session)
    assert purged == 0
    assert (await db_session.execute(
        select(User).where(User.username == "future")
    )).scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_purge_hard_deletes_users_past_pending_deletion_at(db_session):
    await _enable_gdpr(db_session)
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    user = await _make_user(db_session, username="lapsed", pending_at=past)
    user_id = user.id

    purged = await purge_pending_deletions(db_session)
    assert purged == 1

    after = (await db_session.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    assert after is None


@pytest.mark.asyncio
async def test_purge_anonymises_chat_messages_to_null_user_id(db_session):
    """Migration 040 set the FK to ``ON DELETE SET NULL``: when the
    user row goes away, their chat messages survive with ``user_id``
    cleared so the surrounding conversation stays readable."""
    await _enable_gdpr(db_session)
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    user = await _make_user(db_session, username="chat-anon", pending_at=past)
    user_id = user.id

    room = ChatRoom(type="general", name="general")
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)
    msg = ChatMessage(room_id=room.id, user_id=user.id, content="bye")
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)
    msg_id = msg.id

    purged = await purge_pending_deletions(db_session)
    assert purged == 1

    # The FK SET NULL cascade fires at the database layer; expire the
    # cached identity-map row so the next SELECT pulls the post-cascade
    # value.
    db_session.expire(msg)
    survivor = (await db_session.execute(
        select(ChatMessage).where(ChatMessage.id == msg_id)
    )).scalar_one_or_none()
    assert survivor is not None
    assert survivor.user_id is None
    assert survivor.content == "bye"


@pytest.mark.asyncio
async def test_purge_reads_toggle_live_no_cache(db_session):
    """Flipping ``gdpr.enabled`` between two consecutive runs must
    take effect on the second one — no stale cached value."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    await _make_user(db_session, username="live-toggle", pending_at=past)

    # First run: toggle off → no purge.
    assert await purge_pending_deletions(db_session) == 0

    # Flip on → second run purges.
    await _enable_gdpr(db_session)
    assert await purge_pending_deletions(db_session) == 1
