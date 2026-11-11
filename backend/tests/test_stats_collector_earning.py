"""Who earns from an Emby play: every account until it is deactivated, signed in or not."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.user import User
from services.stats_collector.collect import _grant_post_session_xp

TICK = 10_000_000


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


async def _closed_play(db, name: str) -> PlaybackSession:
    now = datetime.now(UTC)
    play = PlaybackSession(
        session_key=f"emby-{name}_movie_1",
        user_id=f"emby-{name}",
        user_name=name,
        item_id="movie-1",
        item_name="Test Movie",
        item_type="Movie",
        duration_ticks=7200 * TICK,
        position_ticks=7000 * TICK,
        started_at=now - timedelta(minutes=5),
        ended_at=now,
        is_active=False,
    )
    db.add(play)
    await db.commit()
    return play


async def _close(db, play: PlaybackSession) -> AsyncMock:
    check = AsyncMock(return_value=[])
    with patch("services.portal.achievements.check_all_achievements", new=check):
        await _grant_post_session_xp(db, [play])
    return check


async def _xp(db, name: str) -> int:
    db.expire_all()
    return (await db.execute(
        select(UserProfile.xp).join(User, User.id == UserProfile.user_id).where(User.username == name)
    )).scalar_one()


@pytest.mark.asyncio
async def test_an_account_never_activated_earns(db_session):
    await _account(db_session, "alice", active=True, signed_in_allowed=False)
    check = await _close(db_session, await _closed_play(db_session, "alice"))
    assert await _xp(db_session, "alice") > 0
    check.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_deactivated_account_earns_nothing(db_session):
    await _account(db_session, "bob", active=False, signed_in_allowed=False)
    check = await _close(db_session, await _closed_play(db_session, "bob"))
    assert await _xp(db_session, "bob") == 0
    check.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_emby_user_seen_for_the_first_time_earns_at_once(db_session):
    check = await _close(db_session, await _closed_play(db_session, "carol"))
    profile = (await db_session.execute(
        select(UserProfile).join(User, User.id == UserProfile.user_id).where(User.username == "carol")
    )).scalar_one()
    assert profile.account_active is False
    assert await _xp(db_session, "carol") > 0
    check.assert_awaited_once()
