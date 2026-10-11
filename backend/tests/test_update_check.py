"""Update check: version ordering, channel rules, opt-outs, cache and API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from constants import env_vars
from services import update_check as uc
from services.settings import get_setting

_ENDPOINT = "/api/system/update-check"


def _response(payload=None, *, status: int = 200, content: bytes | None = None) -> httpx.Response:
    request = httpx.Request("GET", uc._RELEASES_API_URL)
    if content is not None:
        return httpx.Response(status, content=content, request=request)
    return httpx.Response(status, json=payload, request=request)


def _releases(*tags: str) -> httpx.Response:
    return _response([{"tag_name": tag, "draft": False} for tag in tags])


def _client(result: httpx.Response | Exception) -> MagicMock:
    """Fake external HTTP client whose GET returns (or raises) ``result``."""
    client = MagicMock()
    if isinstance(result, Exception):
        client.get = AsyncMock(side_effect=result)
    else:
        client.get = AsyncMock(return_value=result)
    return client


@pytest.mark.parametrize("lower, higher", [
    ("1.0.0-beta.2", "1.0.0-rc.1"),
    ("1.0.0-rc.9", "1.0.0-rc.10"),
    ("1.0.0-rc.10", "1.0.0"),
    ("v1.0.0", "1.0.1-rc.1"),
    ("1.9.9", "1.10.0"),
])
def test_version_ordering(lower, higher):
    assert uc._version_key(lower) < uc._version_key(higher)


@pytest.mark.parametrize("raw", ["", "latest", "1.0", "1.0.0-alpha.1", "1.0.0-rc", " 1.0.0"])
def test_unrecognised_versions_are_ignored(raw):
    assert uc._version_key(raw) is None


def test_prerelease_install_follows_prereleases_and_stables():
    tags = ["v1.0.0-rc.7", "v1.0.0-rc.9", "v1.0.0-rc.8"]
    assert uc._newest_release(tags, "1.0.0-rc.8") == "v1.0.0-rc.9"
    assert uc._newest_release([*tags, "v1.0.0"], "1.0.0-rc.8") == "v1.0.0"


def test_stable_install_ignores_prereleases():
    assert uc._newest_release(["v1.1.0-rc.1", "v1.0.0"], "1.0.0") is None
    assert uc._newest_release(["v1.1.0-rc.1", "v1.0.1"], "1.0.0") == "v1.0.1"


def test_no_newer_release_or_unparsable_current_version():
    assert uc._newest_release(["v1.0.0-rc.8", "nightly"], "1.0.0-rc.8") is None
    assert uc._newest_release(["v2.0.0"], "dev-build") is None


@pytest.mark.asyncio
async def test_status_reports_the_newest_release(db_session):
    client = _client(_releases("v1.0.0-rc.9", "v1.0.0-rc.8"))
    with patch.object(uc, "get_external_client", return_value=client):
        status = await uc.get_update_status(db_session, "1.0.0-rc.8")
    assert status == {
        "enabled": True,
        "locked": False,
        "current_version": "1.0.0-rc.8",
        "latest_version": "1.0.0-rc.9",
        "update_available": True,
        "release_url": "https://github.com/KeeperD93/mediakeeper/releases/tag/v1.0.0-rc.9",
    }
    client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_draft_releases_are_ignored(db_session):
    client = _client(_response([{"tag_name": "v1.0.0-rc.9", "draft": True}]))
    with patch.object(uc, "get_external_client", return_value=client):
        status = await uc.get_update_status(db_session, "1.0.0-rc.8")
    assert status["update_available"] is False


@pytest.mark.asyncio
async def test_admin_switch_off_skips_the_lookup(db_session):
    await uc.set_update_check_enabled(db_session, False)
    client = _client(_releases("v9.9.9"))
    with patch.object(uc, "get_external_client", return_value=client):
        status = await uc.get_update_status(db_session, "1.0.0")
    assert (status["enabled"], status["locked"], status["update_available"]) == (False, False, False)
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_release_list_is_cached_for_six_hours(db_session):
    client = _client(_releases("v1.0.1"))
    with patch.object(uc, "get_external_client", return_value=client):
        await uc.get_update_status(db_session, "1.0.0")
        await uc.get_update_status(db_session, "1.0.0")
        assert client.get.await_count == 1
        expired = datetime.now(timezone.utc) - timedelta(seconds=uc._CACHE_TTL_SECONDS + 1)
        uc._release_cache["at"] = expired
        await uc.get_update_status(db_session, "1.0.0")
    assert client.get.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("result", [
    httpx.ConnectError("unreachable"),
    _response({"message": "API rate limit exceeded"}, status=403),
    _response(content=b"<html>not json</html>"),
    _response({"message": "Not Found"}),
], ids=["network", "http_error", "bad_json", "unexpected_shape"])
async def test_failed_lookup_reports_no_update_and_is_not_retried(db_session, result):
    client = _client(result)
    with patch.object(uc, "get_external_client", return_value=client):
        first = await uc.get_update_status(db_session, "1.0.0")
        await uc.get_update_status(db_session, "1.0.0")
    assert (first["enabled"], first["update_available"], first["latest_version"]) == (True, False, None)
    client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_endpoint_requires_an_admin_session(client):
    r = await client.get(_ENDPOINT)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_endpoint_compares_against_the_running_version(authed_client):
    with patch.object(uc, "get_external_client", return_value=_client(_releases("v1.0.0"))), \
         patch("api.system.APP_VERSION", "1.0.0-rc.8"):
        r = await authed_client.get(_ENDPOINT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["current_version"], body["latest_version"]) == ("1.0.0-rc.8", "1.0.0")
    assert body["update_available"] is True


@pytest.mark.asyncio
async def test_put_endpoint_persists_the_switch(authed_client, db_session):
    client = _client(_releases("v9.9.9"))
    with patch.object(uc, "get_external_client", return_value=client):
        off = await authed_client.put(_ENDPOINT, json={"enabled": False})
        assert off.status_code == 200, off.text
        assert off.json()["enabled"] is False
        assert await get_setting(db_session, uc.UPDATE_CHECK_SETTING_KEY) == "false"
        client.get.assert_not_called()

        on = await authed_client.put(_ENDPOINT, json={"enabled": True})
    assert on.json()["enabled"] is True
    assert on.json()["update_available"] is True


@pytest.mark.asyncio
async def test_put_endpoint_rejects_unknown_fields(authed_client):
    r = await authed_client.put(_ENDPOINT, json={"enabled": True, "channel": "beta"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_env_var_locks_the_check_off(authed_client, monkeypatch):
    monkeypatch.setenv(env_vars.MK_DISABLE_UPDATE_CHECK, "true")
    client = _client(_releases("v9.9.9"))
    with patch.object(uc, "get_external_client", return_value=client):
        r = await authed_client.put(_ENDPOINT, json={"enabled": True})
    body = r.json()
    assert (body["enabled"], body["locked"], body["update_available"]) == (False, True, False)
    client.get.assert_not_called()
