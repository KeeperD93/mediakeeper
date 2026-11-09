"""What someone erased at their request watches is no longer recorded."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession
from models.user import User
from services.portal.gdpr_erased import _identity_keys
from services.settings import set_setting
from services.stats_collector.collect import collect_active_sessions

pytestmark = pytest.mark.asyncio

TICK = 10_000_000
GUID = "EMBY-ALICE"
T0 = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)


def _session(name: str, guid: str, at: datetime) -> dict:
    return {
        "Id": "S-1", "UserId": guid, "UserName": name, "Client": "Web", "DeviceName": "PC",
        "LastActivityDate": at.strftime("%Y-%m-%dT%H:%M:%S.%f") + "0Z",
        "NowPlayingItem": {"Id": "MOVIE-1", "Name": "Test Movie", "Type": "Movie", "RunTimeTicks": 6000 * TICK},
        "PlayState": {"IsPaused": False, "PositionTicks": 60 * TICK},
    }


async def _poll(db, at: datetime, *sessions: dict) -> None:
    source = {"source": "emby", "url": "http://emby.test", "api_key": "k"}
    with patch("services.stats_collector.collect.get_active_media_source", new=AsyncMock(return_value=source)), \
         patch("services.stats_collector.collect.get_raw_sessions", new=AsyncMock(return_value=list(sessions))), \
         patch("services.stats_collector.collect._session_library_name", new=AsyncMock(return_value="Films")):
        await collect_active_sessions(db, now=at)


async def _rows(db) -> list[PlaybackSession]:
    query = select(PlaybackSession).execution_options(populate_existing=True)
    return (await db.execute(query)).scalars().all()


async def _erase_alice(db) -> None:
    for key in _identity_keys(GUID, "alice"):
        await set_setting(db, key, "1")


async def test_what_they_watch_is_no_longer_recorded(db_session):
    await _erase_alice(db_session)
    await _poll(db_session, T0, _session("alice", GUID, T0))
    assert await _rows(db_session) == []


async def test_a_namesake_still_counts_in_the_statistics(db_session):
    await _erase_alice(db_session)
    await _poll(db_session, T0, _session("alice", "EMBY-NEW", T0))
    assert [row.user_id for row in await _rows(db_session)] == ["EMBY-NEW"]


async def test_a_play_open_when_they_are_erased_closes_without_an_account(db_session):
    await _poll(db_session, T0, _session("alice", GUID, T0))
    await _erase_alice(db_session)

    later = T0 + timedelta(seconds=5)
    await _poll(db_session, later, _session("alice", GUID, later))

    (row,) = await _rows(db_session)
    assert row.is_active is False
    assert (await db_session.execute(select(User.id))).first() is None
