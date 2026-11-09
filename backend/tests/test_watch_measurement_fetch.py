"""Reading from Emby the position saved for what is playing now."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.stats_collector._player_reports import (
    StoredPosition,
    fetch_stored_positions,
)
from tests._watch_measurement_helpers import T0, TICK, session

pytestmark = pytest.mark.asyncio


def _client(response: httpx.Response | Exception) -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(side_effect=response) if isinstance(response, Exception) else AsyncMock(return_value=response)
    return client


def _response(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body, request=httpx.Request("GET", "http://emby.test/Users/EMBY-1/Items"))


async def _fetch(client: MagicMock, *sessions: dict) -> dict:
    with patch("services.stats_collector._player_reports.get_internal_client", return_value=client):
        return await fetch_stored_positions("http://emby.test", "k", list(sessions))


async def test_saved_positions_are_read_per_user_with_their_played_mark():
    item = {"Id": "MOVIE-1", "UserData": {"PlaybackPositionTicks": 50 * TICK, "Played": True}}
    client = _client(_response(200, {"Items": [item]}))
    result = await _fetch(client, session(at=T0, position_s=60))
    assert result == {("EMBY-1", "MOVIE-1"): StoredPosition(50 * TICK, True)}
    assert client.get.await_args.kwargs["params"]["Ids"] == "MOVIE-1"


async def test_each_user_is_read_once_for_all_their_titles():
    client = _client(_response(200, {"Items": []}))
    await _fetch(
        client,
        session(at=T0, position_s=60),
        session(at=T0, position_s=60, item="EP-1", item_type="Episode", session="S-2"),
        session(at=T0, position_s=60, user="EMBY-2", session="S-3"),
    )
    assert client.get.await_count == 2
    assert sorted(call.kwargs["params"]["Ids"] for call in client.get.await_args_list) == ["MOVIE-1", "MOVIE-1,EP-1"]


async def test_nothing_is_read_for_what_cannot_be_judged():
    client = _client(_response(200, {"Items": []}))
    await _fetch(
        client,
        session(at=T0, position_s=60, paused=True),
        session(at=T0, position_s=60, item="SONG-1", item_type="Audio"),
        session(at=T0, position_s=60, item="TWICE"),
        session(at=T0, position_s=900, item="TWICE", session="S-2"),
    )
    client.get.assert_not_awaited()


async def test_a_paused_session_does_not_hide_the_one_playing_the_same_title():
    client = _client(_response(200, {"Items": []}))
    await _fetch(client, session(at=T0, position_s=60, paused=True, session="S-2"), session(at=T0, position_s=900))
    client.get.assert_awaited_once()


@pytest.mark.parametrize("failure", [
    httpx.ConnectTimeout("too slow"),
    _response(500, {}),
])
async def test_a_failed_read_returns_nothing(failure):
    assert await _fetch(_client(failure), session(at=T0, position_s=60)) == {}


async def test_an_item_without_user_data_is_absent():
    assert await _fetch(_client(_response(200, {"Items": [{"Id": "MOVIE-1"}]})), session(at=T0, position_s=60)) == {}
