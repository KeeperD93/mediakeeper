"""Tests for the portal trailer endpoints: /random schema + proxy id/type guard."""

from types import SimpleNamespace

import httpx
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


@pytest.mark.asyncio
async def test_stream_emby_trailer_non_json_body_fails_closed():
    # A 200 carrying a non-JSON body (upstream proxy error page, truncated
    # response) must fail closed to ``None`` (→ 404) instead of letting
    # ``.json()`` raise and bubble up as an uncaught 500.
    def _boom():
        raise ValueError("not json")
    bad = SimpleNamespace(status_code=200, json=_boom, headers={}, content=b"<html/>")
    internal = SimpleNamespace(get=AsyncMock(return_value=bad))
    with (
        patch("services.portal.trailers.get_active_media_source",
              AsyncMock(return_value=_EMBY_SOURCE)),
        patch("services.portal.trailers.get_internal_client", return_value=internal),
    ):
        assert await trailers_svc.stream_emby_trailer(None, "trailer123") is None


@pytest.mark.asyncio
async def test_stream_emby_trailer_non_200_returns_none():
    resp = SimpleNamespace(status_code=503, json=lambda: {}, headers={}, content=b"")
    internal = SimpleNamespace(get=AsyncMock(return_value=resp))
    with (
        patch("services.portal.trailers.get_active_media_source",
              AsyncMock(return_value=_EMBY_SOURCE)),
        patch("services.portal.trailers.get_internal_client", return_value=internal),
    ):
        assert await trailers_svc.stream_emby_trailer(None, "trailer123") is None


# --- proxy endpoint behaviour: connect/stream/cap/content-type ---

_RESOLVED_URL = {"url": "http://emby.test/Videos/x1/stream?Static=true&api_key=secret"}


def _streaming_client(send_mock):
    """Fake internal client whose ``send`` is driven by the test."""
    return SimpleNamespace(build_request=lambda *a, **k: object(), send=send_mock)


@pytest.mark.asyncio
async def test_proxy_emby_trailer_404_when_unresolvable(client, db_session):
    await _seed_portal_viewer(client, db_session, "viewer_tr_404")
    with patch("api.portal.trailers.stream_emby_trailer", AsyncMock(return_value=None)):
        resp = await client.get("/api/portal/trailers/emby/trailer123")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_proxy_emby_trailer_502_on_connect_error(client, db_session):
    await _seed_portal_viewer(client, db_session, "viewer_tr_502")
    internal = _streaming_client(AsyncMock(side_effect=httpx.ConnectError("boom")))
    with (
        patch("api.portal.trailers.stream_emby_trailer",
              AsyncMock(return_value=_RESOLVED_URL)),
        patch("api.portal.trailers.get_internal_client", return_value=internal),
    ):
        resp = await client.get("/api/portal/trailers/emby/trailer123")
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_proxy_emby_trailer_404_on_upstream_non_200(client, db_session):
    await _seed_portal_viewer(client, db_session, "viewer_tr_up404")
    upstream = SimpleNamespace(status_code=404, headers={}, aclose=AsyncMock())
    internal = _streaming_client(AsyncMock(return_value=upstream))
    with (
        patch("api.portal.trailers.stream_emby_trailer",
              AsyncMock(return_value=_RESOLVED_URL)),
        patch("api.portal.trailers.get_internal_client", return_value=internal),
    ):
        resp = await client.get("/api/portal/trailers/emby/trailer123")
    assert resp.status_code == 404
    upstream.aclose.assert_awaited()


@pytest.mark.asyncio
async def test_proxy_emby_trailer_propagates_upstream_content_type(client, db_session):
    await _seed_portal_viewer(client, db_session, "viewer_tr_ct")

    async def _chunks():
        yield b"hello "
        yield b"world"

    upstream = SimpleNamespace(
        status_code=200,
        headers={"content-type": "video/webm"},
        aiter_bytes=lambda: _chunks(),
        aclose=AsyncMock(),
    )
    internal = _streaming_client(AsyncMock(return_value=upstream))
    with (
        patch("api.portal.trailers.stream_emby_trailer",
              AsyncMock(return_value=_RESOLVED_URL)),
        patch("api.portal.trailers.get_internal_client", return_value=internal),
    ):
        resp = await client.get("/api/portal/trailers/emby/trailer123")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("video/webm")
    assert resp.content == b"hello world"
    upstream.aclose.assert_awaited()


@pytest.mark.asyncio
async def test_proxy_emby_trailer_truncates_at_cap(client, db_session, monkeypatch):
    await _seed_portal_viewer(client, db_session, "viewer_tr_cap")
    # Shrink the cap so the test doesn't stream a gigabyte; leave the
    # upstream content-type unset to also pin the video/mp4 default.
    monkeypatch.setattr("api.portal.trailers._MAX_TRAILER_BYTES", 5)

    async def _chunks():
        yield b"abc"      # streamed=3, under the cap → forwarded
        yield b"defgh"    # streamed=8 > 5 → truncated, not forwarded
        yield b"ignored"

    upstream = SimpleNamespace(
        status_code=200,
        headers={},
        aiter_bytes=lambda: _chunks(),
        aclose=AsyncMock(),
    )
    internal = _streaming_client(AsyncMock(return_value=upstream))
    with (
        patch("api.portal.trailers.stream_emby_trailer",
              AsyncMock(return_value=_RESOLVED_URL)),
        patch("api.portal.trailers.get_internal_client", return_value=internal),
    ):
        resp = await client.get("/api/portal/trailers/emby/trailer123")
    assert resp.status_code == 200
    assert resp.content == b"abc"
    assert resp.headers["content-type"].startswith("video/mp4")
    upstream.aclose.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_rejects_non_alphanumeric_emby_item_id(client, db_session):
    """A malformed emby_item_id is rejected (422) before it reaches the
    upstream Emby URL builder in resolve_trailer (#420)."""
    await _seed_portal_viewer(client, db_session, "viewer_tr_guard")
    resp = await client.get(
        "/api/portal/trailers/resolve",
        params={"media_type": "movie", "tmdb_id": 1, "emby_item_id": "abc?x=y"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_resolve_returns_candidates_and_best(client, db_session):
    """The resolve endpoint returns the full candidate list plus the best
    one (candidates[0]) so the player can fall back past a blocked trailer."""
    await _seed_portal_viewer(client, db_session, "viewer_tr_cand")
    cands = [
        {"source": "youtube", "key": "AAA",
         "url": "https://www.youtube-nocookie.com/embed/AAA",
         "language": "fr", "name": "BA officielle"},
        {"source": "youtube", "key": "BBB",
         "url": "https://www.youtube-nocookie.com/embed/BBB",
         "language": "en", "name": "Trailer"},
    ]
    with patch("api.portal.trailers.resolve_trailers", AsyncMock(return_value=cands)):
        resp = await client.get(
            "/api/portal/trailers/resolve",
            params={"media_type": "movie", "tmdb_id": 42},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidates"] == cands
    assert data["trailer"] == cands[0]


@pytest.mark.asyncio
async def test_resolve_empty_candidates_returns_null_trailer(client, db_session):
    await _seed_portal_viewer(client, db_session, "viewer_tr_empty")
    with patch("api.portal.trailers.resolve_trailers", AsyncMock(return_value=[])):
        resp = await client.get(
            "/api/portal/trailers/resolve",
            params={"media_type": "movie", "tmdb_id": 43},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trailer"] is None
    assert data["candidates"] == []


@pytest.mark.asyncio
async def test_collect_tmdb_trailers_dedup_cap_and_cascade_order():
    """_collect_tmdb_trailers dedups by provider key, caps at _MAX_CANDIDATES,
    drops non-YouTube/Vimeo, walks the user language before English, and its
    first entry equals what _pick_video (the single-best picker) returns."""
    videos = [
        {"key": "FR1", "site": "YouTube", "type": "Trailer", "official": True,
         "iso_639_1": "fr", "published_at": "2024-01-01", "name": "Bande-annonce officielle"},
        {"key": "FR1", "site": "YouTube", "type": "Trailer", "official": True,
         "iso_639_1": "fr", "published_at": "2024-01-01", "name": "duplicate key"},
        {"key": "EN1", "site": "YouTube", "type": "Trailer", "official": True,
         "iso_639_1": "en", "published_at": "2024-01-01", "name": "Trailer"},
        {"key": "FR2", "site": "YouTube", "type": "Trailer", "official": False,
         "iso_639_1": "fr", "published_at": "2023-06-01", "name": "t2"},
        {"key": "FR3", "site": "YouTube", "type": "Trailer", "official": False,
         "iso_639_1": "fr", "published_at": "2023-05-01", "name": "t3"},
        {"key": "FR4", "site": "YouTube", "type": "Trailer", "official": False,
         "iso_639_1": "fr", "published_at": "2023-04-01", "name": "t4"},
        {"key": "FR5", "site": "YouTube", "type": "Trailer", "official": False,
         "iso_639_1": "fr", "published_at": "2023-03-01", "name": "t5"},
        {"key": "FR6", "site": "YouTube", "type": "Trailer", "official": False,
         "iso_639_1": "fr", "published_at": "2023-02-01", "name": "t6"},
        {"key": "FR7", "site": "YouTube", "type": "Trailer", "official": False,
         "iso_639_1": "fr", "published_at": "2023-01-01", "name": "t7"},
        {"key": "FB", "site": "Facebook", "type": "Trailer", "official": True,
         "iso_639_1": "fr", "name": "social only"},
    ]
    payload = SimpleNamespace(
        status_code=200,
        json=lambda: {"videos": {"results": videos}, "original_language": "fr"},
    )
    fake_client = SimpleNamespace(get=AsyncMock(return_value=payload))
    with (
        patch("services.portal.trailers._get_tmdb_key", AsyncMock(return_value="k")),
        patch("services.portal.trailers.get_external_client", return_value=fake_client),
    ):
        out = await trailers_svc._collect_tmdb_trailers(None, "movie", 1, "fr")

    keys = [d["key"] for d in out]
    assert keys[0] == "FR1"                            # best = fr official studio dub
    assert len(out) == trailers_svc._MAX_CANDIDATES    # capped
    assert len(set(keys)) == len(keys)                 # deduped by provider key
    assert "FB" not in keys                            # non-YouTube/Vimeo dropped
    assert "EN1" not in keys                           # fr fills the cap before the en step
    # candidates[0] is exactly what the single-best picker returns.
    assert out[0]["key"] == trailers_svc._pick_video(videos, "fr")["key"]
    # original_language == user_language → no second /videos round-trip.
    assert fake_client.get.await_count == 1
