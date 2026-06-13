"""Tests for the portal trailer endpoints: /random schema + proxy id/type guard."""

from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, patch

from core.security import create_access_token, hash_password
from models.user import User
from models.portal.profile import UserProfile
from services.portal import trailers as trailers_svc


async def _seed_portal_viewer(client, db_session, username: str = "viewer_trailer"):
    """Create a viewer + portal profile and attach a Portal-scoped token."""
    user = User(
        username=username,
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
    ))
    await db_session.commit()

    token = create_access_token({"sub": username, "scope": "portal"})
    client.cookies.set("rq_token", token)
    return user


@pytest.mark.asyncio
async def test_random_trailers_returns_extended_schema(client, db_session):
    """Each item must expose the 7 keys the cinema room carousel needs."""
    await _seed_portal_viewer(client, db_session)

    fake_items = [
        {
            "id": 1234,
            "emby_item_id": "emby-abc",
            "tmdb_id": 1234,
            "title": "Test Movie",
            "media_type": "movie",
            "emby_url": "https://emby.example/web/index.html#!/item?id=emby-abc",
            "poster_url": "/api/emby/image/emby-abc?type=Primary",
        },
        {
            "id": 5678,
            "emby_item_id": "emby-def",
            "tmdb_id": 5678,
            "title": "Test Series",
            "media_type": "tv",
            "emby_url": "https://emby.example/web/index.html#!/item?id=emby-def",
            "poster_url": "/api/emby/image/emby-def?type=Primary",
        },
    ]

    fake_trailer = {
        "source": "youtube",
        "key": "abcdefghijk",
        "url": "https://www.youtube.com/embed/abcdefghijk",
        "language": "en",
        "name": "Official Trailer",
    }

    with (
        patch(
            "services.portal.available.get_recently_added",
            AsyncMock(return_value=fake_items),
        ),
        patch(
            "api.portal.trailers.resolve_trailer",
            AsyncMock(return_value=fake_trailer),
        ),
    ):
        resp = await client.get("/api/portal/trailers/random?limit=5")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 2

    expected_keys = {
        "key", "title", "source",
        "emby_item_id", "tmdb_id", "media_type", "emby_url",
    }
    for item in data["items"]:
        assert set(item.keys()) == expected_keys
        assert item["key"] == "abcdefghijk"
        assert item["source"] == "youtube"
        assert item["media_type"] in ("movie", "tv")
        assert isinstance(item["tmdb_id"], int)
        assert item["emby_item_id"].startswith("emby-")
        assert item["emby_url"].startswith("https://")


@pytest.mark.asyncio
async def test_random_trailers_handles_missing_emby_url(client, db_session):
    """When a source has no public URL, emby_url falls back to None."""
    await _seed_portal_viewer(client, db_session)

    fake_items = [
        {
            "id": 9999,
            "emby_item_id": "emby-xyz",
            "tmdb_id": 9999,
            "title": "Local Only",
            "media_type": "movie",
            "emby_url": "",
        },
    ]
    fake_trailer = {
        "source": "youtube",
        "key": "zzzzzzzzzzz",
        "url": "https://www.youtube.com/embed/zzzzzzzzzzz",
        "language": "en",
        "name": "Trailer",
    }

    with (
        patch(
            "services.portal.available.get_recently_added",
            AsyncMock(return_value=fake_items),
        ),
        patch(
            "api.portal.trailers.resolve_trailer",
            AsyncMock(return_value=fake_trailer),
        ),
    ):
        resp = await client.get("/api/portal/trailers/random?limit=1")

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["emby_url"] is None
    assert item["emby_item_id"] == "emby-xyz"


_EMBY_SOURCE = {"source": "emby", "url": "http://emby.test", "api_key": "secret"}


def _emby_item_resp(item_type):
    """Fake Emby /Items?Ids= response carrying one item of the given Type."""
    return SimpleNamespace(
        status_code=200,
        json=lambda: {"Items": [{"Id": "x1", "Type": item_type}]},
        headers={},
        content=b"",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_id", ["abc?x=y", "../secret", "a/b", "id space", ""])
async def test_stream_emby_trailer_rejects_malformed_id(bad_id):
    # The format guard runs before any Emby call, so a forged id never
    # reaches the upstream stream URL.
    assert await trailers_svc.stream_emby_trailer(None, bad_id) is None


@pytest.mark.asyncio
async def test_stream_emby_trailer_refuses_non_trailer_item():
    client = SimpleNamespace(get=AsyncMock(return_value=_emby_item_resp("Movie")))
    with (
        patch("services.portal.trailers.get_active_media_source",
              AsyncMock(return_value=_EMBY_SOURCE)),
        patch("services.portal.trailers.get_internal_client", return_value=client),
    ):
        # A movie/episode id must not be streamable through the trailer proxy.
        assert await trailers_svc.stream_emby_trailer(None, "movie123") is None


@pytest.mark.asyncio
async def test_stream_emby_trailer_allows_real_trailer():
    client = SimpleNamespace(get=AsyncMock(return_value=_emby_item_resp("Trailer")))
    with (
        patch("services.portal.trailers.get_active_media_source",
              AsyncMock(return_value=_EMBY_SOURCE)),
        patch("services.portal.trailers.get_internal_client", return_value=client),
    ):
        info = await trailers_svc.stream_emby_trailer(None, "trailer123")
    assert info is not None
    assert "/Videos/trailer123/stream" in info["url"]
