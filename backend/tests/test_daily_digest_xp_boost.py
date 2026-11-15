"""XP boosts in the daily digest: the running ones, first to end first, with the
actions they are limited to and their end on the server's clock, read fresh on
every call and worth opening the digest for. The XP grants keep following the
same filters."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import daily_digest as dd_svc
from services.portal import daily_digest_cache as digest_cache
from services.portal import daily_digest_sources as sources
from services.portal import xp_boost
from services.settings import set_setting
from tests._portal_profile_helpers import make_portal_user


@pytest.fixture
def quiet_sources():
    """Every other block is empty, so the boosts are judged alone."""
    quota = {"used": 0, "max_allowed": 0, "unlimited": False, "remaining": 0}
    recent = AsyncMock(return_value=[])
    stubs = [
        patch.object(sources, "recent_adds", recent),
        patch.object(sources, "upcoming_events", AsyncMock(return_value=[])),
        patch.object(sources, "ranking_snapshot", AsyncMock(
            return_value={"position": 0, "total": 0, "movement": 0, "top3": []},
        )),
        patch.object(sources, "quota_snapshot", AsyncMock(return_value=quota)),
        patch.object(sources, "open_tickets_count", AsyncMock(return_value=0)),
        patch.object(sources, "current_streak", AsyncMock(return_value=0)),
        patch.object(sources, "closest_achievement", AsyncMock(return_value=None)),
    ]
    for stub in stubs:
        stub.start()
    yield recent
    for stub in stubs:
        stub.stop()


async def _boost(db, name, *, starts_in=-1.0, ends_in=5.0, **extra):
    now = datetime.now(UTC)
    return await xp_boost.create_event(db, {
        "name": name,
        "starts_at": now + timedelta(days=starts_in),
        "ends_at": now + timedelta(days=ends_in),
        **extra,
    })


@pytest.mark.asyncio
async def test_only_running_enabled_boosts_show_first_to_end_first(db_session):
    await _boost(db_session, "Test Boost Later", ends_in=5)
    await _boost(db_session, "Test Boost Sooner", ends_in=2, multiplier=1.5,
                 description="Test description")
    await _boost(db_session, "Test Boost Off", enabled=False)
    await _boost(db_session, "Test Boost Future", starts_in=1, ends_in=3)
    await _boost(db_session, "Test Boost Past", starts_in=-3, ends_in=-1)

    boosts = await xp_boost.active_boosts(db_session, datetime.now(UTC), UTC)

    assert [b["name"] for b in boosts] == ["Test Boost Sooner", "Test Boost Later"]
    first = boosts[0]
    assert (first["multiplier"], first["description"], first["actions"]) == (
        1.5, "Test description", [],
    )
    assert first["ends_at"].endswith("+00:00")


@pytest.mark.asyncio
async def test_the_end_is_written_on_the_clock_of_the_server(db_session):
    await xp_boost.create_event(db_session, {
        "name": "Test Boost",
        "starts_at": datetime(2027, 1, 1, tzinfo=UTC),
        "ends_at": datetime(2027, 1, 3, 22, 59, tzinfo=UTC),
    })
    moment = datetime(2027, 1, 2, tzinfo=UTC)

    [paris] = await xp_boost.active_boosts(db_session, moment, ZoneInfo("Europe/Paris"))
    [utc] = await xp_boost.active_boosts(db_session, moment, UTC)

    assert paris["ends_local"] == "2027-01-03T23:59:00"
    assert utc["ends_local"] == "2027-01-03T22:59:00"
    assert paris["ends_at"] == utc["ends_at"] == "2027-01-03T22:59:00+00:00"


@pytest.mark.asyncio
async def test_a_limited_boost_lists_its_actions_once_in_the_admin_order(db_session):
    await _boost(db_session, "Test Boost", action_filter=" watch_movie, watch_episode,watch_movie ,")

    [boost] = await xp_boost.active_boosts(db_session, datetime.now(UTC), UTC)

    assert boost["actions"] == ["watch_movie", "watch_episode"]


@pytest.mark.asyncio
async def test_a_filter_of_separators_only_counts_for_nothing(db_session):
    await _boost(db_session, "Test Boost", multiplier=3.0, action_filter=" , ,")

    assert await xp_boost.active_boosts(db_session, datetime.now(UTC), UTC) == []
    assert await xp_boost.get_active_multiplier(db_session, "watch_movie") == 1.0


@pytest.mark.asyncio
async def test_the_grants_still_multiply_the_boosts_their_action_matches(db_session):
    await _boost(db_session, "Test Boost All", multiplier=2.0)
    await _boost(db_session, "Test Boost Movies", multiplier=1.5, action_filter="watch_movie")
    await _boost(db_session, "Test Boost Off", multiplier=10.0, enabled=False)

    assert await xp_boost.get_active_multiplier(db_session, "watch_movie") == 3.0
    assert await xp_boost.get_active_multiplier(db_session, "watch_episode") == 2.0


@pytest.mark.asyncio
async def test_a_running_boost_alone_opens_the_digest(db_session, quiet_sources):
    user, _ = await make_portal_user(db_session, username="alice")

    digest = await dd_svc.build_digest(db_session, user, use_cache=False)
    assert (digest["xp_boosts"], digest["empty"]) == ([], True)

    await _boost(db_session, "Test Boost")
    digest = await dd_svc.build_digest(db_session, user, use_cache=False)
    assert [b["name"] for b in digest["xp_boosts"]] == ["Test Boost"]
    assert digest["empty"] is False


@pytest.mark.asyncio
async def test_the_digest_writes_the_end_in_the_saved_zone(db_session, quiet_sources):
    user, _ = await make_portal_user(db_session, username="alice")
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    created = await _boost(db_session, "Test Boost")

    [shown] = (await dd_svc.build_digest(db_session, user, use_cache=False))["xp_boosts"]

    in_paris = datetime.fromisoformat(created["ends_at"]).astimezone(ZoneInfo("Europe/Paris"))
    assert shown["ends_local"] == in_paris.replace(tzinfo=None).isoformat(timespec="seconds")


@pytest.mark.asyncio
async def test_boosts_are_read_fresh_over_a_cached_digest(db_session, quiet_sources):
    user, _ = await make_portal_user(db_session, username="alice")
    assert (await dd_svc.build_digest(db_session, user))["empty"] is True

    await _boost(db_session, "Test Boost")
    digest = await dd_svc.build_digest(db_session, user)

    assert quiet_sources.await_count == 1  # served from the cache
    assert [b["name"] for b in digest["xp_boosts"]] == ["Test Boost"]
    assert digest["empty"] is False
    [(_, cached)] = digest_cache._digest_cache.values()
    assert "xp_boosts" not in cached
    assert cached["empty"] is True
