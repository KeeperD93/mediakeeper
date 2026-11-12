"""Who earns from an Emby play: every account until it is deactivated, signed in or not."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackCompletion, PlaybackSession
from models.portal.profile import UserProfile
from models.user import User
from services.stats_collector.collect import _after_rows_closed, pay_watch_xp

TICK = 10_000_000
RUNTIME = 7200  # a 2-hour film: 40 XP


async def _account(db, name: str, *, active: bool, signed_in_allowed: bool) -> UserProfile:
    user = User(username=name, hashed_password="x", is_active=active, must_change_password=False)
    db.add(user)
    await db.flush()
    profile = UserProfile(
        user_id=user.id, display_name=name, role="viewer",
        account_active=signed_in_allowed, emby_user_id=f"emby-{name}",
    )
    db.add(profile)
    await db.commit()
    return profile


async def _watch_and_close(db, name: str) -> AsyncMock:
    """A film watched to the end, then its row closed: pay, then check the trophies."""
    now = datetime.now(UTC)
    play = PlaybackSession(
        session_key=f"emby-{name}_movie_1", user_id=f"emby-{name}", user_name=name,
        item_id="movie-1", item_name="Test Movie", item_type="Movie",
        duration_ticks=RUNTIME * TICK, position_ticks=RUNTIME * TICK,
        started_at=now - timedelta(seconds=RUNTIME), ended_at=now, is_active=False,
        watched_seconds=RUNTIME, exclusive_seconds=RUNTIME, completed_at=now,
    )
    db.add(play)
    await db.flush()
    done = PlaybackCompletion(
        session_id=play.id, user_id=play.user_id, user_name=name, item_id="movie-1", item_type="Movie",
        item_name="Test Movie", runtime_seconds=RUNTIME, watched_seconds=RUNTIME, exclusive_seconds=RUNTIME,
        completed_at=now,
    )
    db.add(done)
    await db.commit()
    play_id, done_id = play.id, done.id

    check = AsyncMock(return_value=[])
    with patch("services.portal.achievements.check_all_achievements", new=check):
        await pay_watch_xp(db, [done_id])
        await _after_rows_closed(db, [play_id])
    return check


async def _xp(db, name: str) -> int:
    db.expire_all()
    return (await db.execute(
        select(UserProfile.xp).join(User, User.id == UserProfile.user_id).where(User.username == name)
    )).scalar_one()


@pytest.mark.asyncio
async def test_an_account_never_activated_earns(db_session):
    await _account(db_session, "alice", active=True, signed_in_allowed=False)
    check = await _watch_and_close(db_session, "alice")
    assert await _xp(db_session, "alice") == 40
    check.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_deactivated_account_earns_nothing(db_session):
    await _account(db_session, "bob", active=False, signed_in_allowed=False)
    check = await _watch_and_close(db_session, "bob")
    assert await _xp(db_session, "bob") == 0
    check.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_emby_user_seen_for_the_first_time_gets_an_account_and_earns_at_once(db_session):
    check = await _watch_and_close(db_session, "carol")
    profile = (await db_session.execute(
        select(UserProfile).join(User, User.id == UserProfile.user_id).where(User.username == "carol")
    )).scalar_one()
    assert profile.account_active is False
    assert await _xp(db_session, "carol") == 40
    check.assert_awaited_once()
