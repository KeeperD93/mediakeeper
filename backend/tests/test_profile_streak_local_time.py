"""The day streak, and that of the profile and the daily digest in the saved zone."""
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.user import User
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import daily_digest_sources, profile_stats, profile_stats_playback
from services.portal.play_streak import current_streak, longest_streak
from services.settings import set_setting

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 10, 16, 18, tzinfo=UTC)


class _Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


async def _viewer(db) -> tuple[User, UserProfile]:
    user = User(username="alice", hashed_password="x", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(UserProfile(user_id=user.id, display_name="alice", role="viewer", account_active=True))
    await db.commit()
    profile = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()
    return user, profile


def _session(db, started: datetime) -> None:
    db.add(PlaybackSession(
        session_key=f"alice-{started.timestamp()}",
        user_id="emby-alice",
        user_name="alice",
        item_id="item-1",
        item_name="Test Movie",
        item_type="Movie",
        started_at=started,
        last_seen_at=started,
        ended_at=started + timedelta(minutes=1),
    ))


def test_current_streak_ends_today_or_yesterday():
    today = date(2026, 10, 16)
    days = {today, today - timedelta(days=1), today - timedelta(days=2)}
    assert current_streak(days, today) == 3
    assert current_streak(days, today + timedelta(days=1)) == 3
    assert current_streak(days, today + timedelta(days=2)) == 0
    assert current_streak(set(), today) == 0
    assert current_streak({today - timedelta(days=2)}, today) == 0


def test_longest_streak_finds_the_best_run_anywhere():
    start = date(2026, 1, 1)
    days = [start + timedelta(days=n) for n in (0, 1, 2, 3, 10, 11, 20)]
    assert longest_streak(days) == 4
    assert longest_streak([]) == 0
    assert longest_streak([start, start]) == 1


@pytest.mark.asyncio
async def test_the_profile_reads_the_saved_zone_before_its_fan_out(db_session):
    user, profile = await _viewer(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    streak = AsyncMock(return_value=4)
    empty = AsyncMock(return_value=[])
    with patch.multiple(
        profile_stats,
        _compute_streak=streak,
        compute_totals=AsyncMock(return_value=(0, 0)),
        compute_record_day=AsyncMock(return_value={}),
        compute_most_rewatched=AsyncMock(return_value=(None, None, None)),
        compute_genre_stats=empty,
        compute_day_stats=AsyncMock(return_value=None),
        compute_longest_session=AsyncMock(return_value=0),
        compute_media_type_ratio=AsyncMock(return_value={}),
        compute_hour_buckets=empty,
        compute_record_month=AsyncMock(return_value={}),
        compute_ranking=AsyncMock(return_value={}),
        fetch_recent_watches=empty,
        fetch_next_to_finish=empty,
        fetch_my_requests=empty,
    ):
        out = await profile_stats.get_profile_full(db_session, user, profile)

    assert out["stats"]["streak"] == 4
    assert streak.await_args.args[3].key == "Europe/Paris"


@pytest.mark.asyncio
async def test_the_streak_follows_the_saved_zone(db_session, monkeypatch):
    """22:22 UTC is 00:22 the next day in Paris: without it, a day looks empty."""
    user, profile = await _viewer(db_session)
    _session(db_session, datetime(2026, 10, 14, 22, 22, tzinfo=UTC))
    _session(db_session, datetime(2026, 10, 16, 16, 49, tzinfo=UTC))
    await db_session.commit()
    monkeypatch.setattr(profile_stats_playback, "datetime", _Frozen)
    players = PlaybackSession.user_name == "alice"

    assert await profile_stats_playback.compute_streak(db_session, players, [], UTC) == 1
    assert await profile_stats_playback.compute_streak(db_session, players, [], PARIS) == 2
    assert await daily_digest_sources.current_streak(db_session, user, profile) == 1

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    assert await daily_digest_sources.current_streak(db_session, user, profile) == 2


@pytest.mark.asyncio
async def test_today_itself_follows_the_zone(db_session, monkeypatch):
    """At 18:00 UTC on the 16th it is already the 17th in Auckland: the 15th no longer counts."""
    _session(db_session, datetime(2026, 10, 15, 0, 30, tzinfo=UTC))
    await db_session.commit()
    monkeypatch.setattr(profile_stats_playback, "datetime", _Frozen)
    players = PlaybackSession.user_name == "alice"
    auckland = ZoneInfo("Pacific/Auckland")

    assert await profile_stats_playback.compute_streak(db_session, players, [], UTC) == 1
    assert await profile_stats_playback.compute_streak(db_session, players, [], auckland) == 0


@pytest.mark.asyncio
async def test_the_streak_leaves_out_excluded_titles(db_session, monkeypatch):
    _session(db_session, datetime(2026, 10, 16, 12, tzinfo=UTC))
    _session(db_session, datetime(2026, 10, 15, 12, tzinfo=UTC))
    await db_session.commit()
    monkeypatch.setattr(profile_stats_playback, "datetime", _Frozen)
    players = PlaybackSession.user_name == "alice"
    excluded = [PlaybackSession.started_at < datetime(2026, 10, 16, tzinfo=UTC)]

    assert await profile_stats_playback.compute_streak(db_session, players, [], PARIS) == 2
    assert await profile_stats_playback.compute_streak(db_session, players, excluded, PARIS) == 1


@pytest.mark.asyncio
async def test_a_date_at_the_edge_of_the_calendar_keeps_the_streak(db_session, monkeypatch):
    _session(db_session, datetime(1, 1, 1, tzinfo=UTC))
    _session(db_session, datetime(2026, 10, 16, 12, tzinfo=UTC))
    await db_session.commit()
    monkeypatch.setattr(profile_stats_playback, "datetime", _Frozen)
    players = PlaybackSession.user_name == "alice"
    new_york = ZoneInfo("America/New_York")

    assert await profile_stats_playback.compute_streak(db_session, players, [], new_york) == 1


@pytest.mark.asyncio
async def test_the_streak_is_zero_after_a_failed_read(db_session, monkeypatch):
    players = PlaybackSession.user_name == "alice"
    monkeypatch.setattr(db_session, "execute", AsyncMock(side_effect=RuntimeError("Test error")))
    assert await profile_stats_playback.compute_streak(db_session, players, [], PARIS) == 0
