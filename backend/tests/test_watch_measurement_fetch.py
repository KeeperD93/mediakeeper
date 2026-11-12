"""Reading from Emby the position saved for what is playing now, and where it saves one."""
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.stats_collector import _resume_zones as zones
from services.stats_collector._player_reports import (
    StoredPosition,
    fetch_stored_positions,
)
from services.stats_collector._resume_zones import ResumeZone, refresh_resume_zones
from tests._watch_measurement_helpers import T0, TICK, emby_session

pytestmark = pytest.mark.asyncio


def _client(response: httpx.Response | Exception) -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(side_effect=response) if isinstance(response, Exception) else AsyncMock(return_value=response)
    return client


def _response(status: int, body: dict | list) -> httpx.Response:
    return httpx.Response(status, json=body, request=httpx.Request("GET", "http://emby.test/Users/EMBY-1/Items"))


async def _fetch(client: MagicMock, *sessions: dict) -> dict:
    with patch("services.stats_collector._player_reports.get_internal_client", return_value=client):
        return await fetch_stored_positions("http://emby.test", "k", list(sessions))


async def test_saved_positions_are_read_per_user_with_their_played_mark():
    item = {"Id": "MOVIE-1", "UserData": {"PlaybackPositionTicks": 50 * TICK, "Played": True}}
    client = _client(_response(200, {"Items": [item]}))
    result = await _fetch(client, emby_session(at=T0, position_s=60))
    assert result == {("EMBY-1", "MOVIE-1"): StoredPosition(50 * TICK, True)}
    assert client.get.await_args.kwargs["params"]["Ids"] == "MOVIE-1"


async def test_each_user_is_read_once_for_all_their_titles():
    client = _client(_response(200, {"Items": []}))
    await _fetch(
        client,
        emby_session(at=T0, position_s=60),
        emby_session(at=T0, position_s=60, item="EP-1", item_type="Episode", session="S-2"),
        emby_session(at=T0, position_s=60, user="EMBY-2", session="S-3"),
    )
    assert client.get.await_count == 2
    assert sorted(call.kwargs["params"]["Ids"] for call in client.get.await_args_list) == ["MOVIE-1", "MOVIE-1,EP-1"]


async def test_nothing_is_read_for_what_cannot_be_judged():
    client = _client(_response(200, {"Items": []}))
    await _fetch(
        client,
        emby_session(at=T0, position_s=60, paused=True),
        emby_session(at=T0, position_s=60, item="SONG-1", item_type="Audio"),
        emby_session(at=T0, position_s=60, item="TWICE"),
        emby_session(at=T0, position_s=900, item="TWICE", session="S-2"),
    )
    client.get.assert_not_awaited()


async def test_a_paused_session_does_not_hide_the_one_playing_the_same_title():
    client = _client(_response(200, {"Items": []}))
    await _fetch(client, emby_session(at=T0, position_s=60, paused=True, session="S-2"), emby_session(at=T0, position_s=900))
    client.get.assert_awaited_once()


@pytest.mark.parametrize("failure", [
    httpx.ConnectTimeout("too slow"),
    _response(500, {}),
])
async def test_a_failed_read_returns_nothing(failure):
    assert await _fetch(_client(failure), emby_session(at=T0, position_s=60)) == {}


async def test_an_item_without_user_data_is_absent():
    assert await _fetch(_client(_response(200, {"Items": [{"Id": "MOVIE-1"}]})), emby_session(at=T0, position_s=60)) == {}


def _library(name: str, **options) -> dict:
    return {"Name": name, "ItemId": f"id-{name}", "LibraryOptions": {"MaxResumePct": 90, **options}}


async def _refresh(client: MagicMock, at=T0) -> None:
    with patch("services.stats_collector._resume_zones.get_internal_client", return_value=client):
        await refresh_resume_zones("http://emby.test", "k", at)


async def test_resume_settings_are_read_per_library():
    client = _client(_response(200, [
        _library("Movies", MinResumePct=3, MinResumeDurationSeconds=120),
        _library("Shows", MinResumePct=5, MinResumeDurationSeconds=300),
        _library("Home videos"),
        _library("Clips", MinResumePct=-1, MinResumeDurationSeconds=120),
    ]))
    await _refresh(client)
    assert zones._zones == {"Movies": ResumeZone(3, 120 * TICK), "Shows": ResumeZone(5, 300 * TICK)}
    assert client.get.await_args.args[0] == "http://emby.test/Library/VirtualFolders"


async def test_resume_settings_are_read_at_most_hourly():
    client = _client(_response(200, [_library("Movies", MinResumePct=3, MinResumeDurationSeconds=120)]))
    for at in (T0, T0 + timedelta(minutes=59), T0 + timedelta(hours=1)):
        await _refresh(client, at)
    assert client.get.await_count == 2


@pytest.mark.parametrize("failure", [httpx.ConnectTimeout("too slow"), _response(500, {}), _response(200, {"Items": []})])
async def test_a_failed_read_keeps_the_resume_settings_read_before(failure):
    await _refresh(_client(_response(200, [_library("Movies", MinResumePct=3, MinResumeDurationSeconds=120)])))
    await _refresh(_client(failure), T0 + timedelta(hours=1))
    assert zones._zones == {"Movies": ResumeZone(3, 120 * TICK)}


@pytest.mark.parametrize("runtime_s, start_s", [(6000, 180), (100, None), (0, None)])
async def test_a_title_shorter_than_the_minimum_is_never_resumed(runtime_s, start_s):
    start = ResumeZone(3, 120 * TICK).start_ticks(runtime_s * TICK)
    assert start == (None if start_s is None else start_s * TICK)
