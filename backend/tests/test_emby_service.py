from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import services.emby as emby_service


def _fake_response(*, status_code=200, payload=None, content=b"", headers=None):
    return SimpleNamespace(
        status_code=status_code,
        json=lambda: payload,
        content=content,
        headers=headers or {},
    )


@pytest.mark.asyncio
async def test_get_raw_sessions_reuses_shared_cache(db_session):
    emby_service.invalidate_emby_config_cache()

    client = SimpleNamespace(
        get=AsyncMock(return_value=_fake_response(
            payload=[{"Id": "sess-1", "UserName": "alice", "NowPlayingItem": {"Id": "movie-1"}}]
        ))
    )

    with patch("services.emby.config.get_active_media_source", new=AsyncMock(return_value={
        "source": "emby",
        "url": "http://emby.test",
        "api_key": "secret",
    })), patch("services.emby.sessions.get_internal_client", return_value=client):
        first = await emby_service.get_raw_sessions(db_session)
        second = await emby_service.get_raw_sessions(db_session)

    assert first == second
    assert client.get.await_count == 1
    emby_service.invalidate_emby_config_cache()


@pytest.mark.asyncio
async def test_proxy_image_reuses_memory_cache(db_session):
    emby_service.invalidate_emby_config_cache()

    client = SimpleNamespace(
        get=AsyncMock(return_value=_fake_response(
            content=b"poster-bytes",
            headers={"content-type": "image/jpeg"},
        ))
    )

    with patch("services.emby.config.get_active_media_source", new=AsyncMock(return_value={
        "source": "emby",
        "url": "http://emby.test",
        "api_key": "secret",
    })), patch("services.emby.images.get_internal_client", return_value=client):
        first = await emby_service.proxy_image(db_session, "12345")
        second = await emby_service.proxy_image(db_session, "12345")

    assert first == (b"poster-bytes", "image/jpeg")
    assert second == first
    assert client.get.await_count == 1
    emby_service.invalidate_emby_config_cache()
