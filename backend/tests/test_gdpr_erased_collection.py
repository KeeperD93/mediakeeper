"""What someone erased at their request watches is no longer recorded."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession
from models.user import User
from services.portal.gdpr import purge_pending_deletions
from services.portal.gdpr_erased import _identity_keys
from services.settings import set_setting
from services.stats import import_jellystats_backup
from services.stats_collector.collect import collect_active_sessions
from tests._gdpr_erased_helpers import GUID, gdpr_on, member, purged

pytestmark = pytest.mark.asyncio

TICK = 10_000_000
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
         patch("services.stats_collector.collect.fetch_stored_positions", new=AsyncMock(return_value={})), \
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


async def test_the_other_profile_of_a_shared_emby_id_keeps_being_recorded(db_session):
    await gdpr_on(db_session)
    await member(db_session, "alice-old")
    await member(db_session, "alice-new", overdue=False)
    assert await purge_pending_deletions(db_session) == 1

    await _poll(db_session, T0, _session("alice-new", GUID, T0))

    assert [row.user_name for row in await _rows(db_session)] == ["alice-new"]


def _played(number: int, guid: str) -> dict:
    return {
        "Id": f"JS-{number}", "rowid": number, "UserId": guid, "UserName": "Test User",
        "NowPlayingItemId": "MOVIE-1", "NowPlayingItemName": "Test Movie", "PlaybackDuration": 600,
        "ItemId": "MOVIE-1", "ItemName": "Test Movie", "ItemType": "Movie", "PlayDuration": 600,
        "ActivityDateInserted": "2026-03-07T20:00:00Z", "DateCreated": "2026-03-07T20:00:00Z",
    }


async def test_a_statistics_import_leaves_out_an_erased_id(db_session):
    await purged(db_session)

    report = await import_jellystats_backup(db_session, {
        "jf_playback_activity": [_played(1, GUID), _played(2, "EMBY-BOB")],
        "jf_playback_reporting_plugin_data": [_played(3, GUID), _played(4, "EMBY-BOB")],
    })

    assert sorted(row.session_key for row in await _rows(db_session)) == ["js_JS-2", "jsplugin_4"]
    assert (report["playback_imported"], report["playback_skipped"]) == (1, 0)
    assert (report["plugin_imported"], report["plugin_skipped"]) == (1, 0)


async def test_a_statistics_import_does_not_write_an_erased_name_back(db_session):
    await purged(db_session)
    for number, guid in ((1, GUID), (2, "EMBY-BOB")):
        db_session.add(PlaybackSession(
            session_key=f"jsplugin_{number}", user_id=guid, user_name="", item_id="MOVIE-1",
            item_name="Test Movie", item_type="Movie", duration_ticks=0, position_ticks=0,
            started_at=T0, ended_at=T0, is_active=False,
        ))
    await db_session.commit()

    await import_jellystats_backup(db_session, {
        "jf_users": [{"Id": GUID, "Name": "alice"}, {"Id": "EMBY-BOB", "Name": "bob"}],
    })

    assert {row.user_id: row.user_name for row in await _rows(db_session)} == {GUID: "", "EMBY-BOB": "bob"}


async def test_a_play_open_when_they_are_erased_closes_without_an_account(db_session):
    await _poll(db_session, T0, _session("alice", GUID, T0))
    await _erase_alice(db_session)

    later = T0 + timedelta(seconds=5)
    await _poll(db_session, later, _session("alice", GUID, later))

    (row,) = await _rows(db_session)
    assert row.is_active is False
    assert (await db_session.execute(select(User.id))).first() is None
