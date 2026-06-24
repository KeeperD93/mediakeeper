"""Functional HTTP tests for the mounted admin media routes.

These complement ``test_media_cycle20_error_codes.py`` (service/handler-level
error codes) and ``test_metadata_parse.py`` (pure parsers): here we exercise the
real ``/api/media`` routes end-to-end through the ``get_current_user`` auth
dependency, the ``get_request_locale`` dependency, the URL prefix and the
query-param wiring. The external services (TMDB, ffprobe, filesystem listing)
are stubbed so the tests pin the route plumbing, not the upstreams.
"""
from unittest.mock import AsyncMock

import pytest


# --- TMDB proxy routes (api/media/_tmdb.py) ---------------------------------


@pytest.mark.asyncio
async def test_tmdb_search_movie_route_forwards_query(authed_client, monkeypatch):
    stub = AsyncMock(return_value={"results": [{"id": 603}]})
    monkeypatch.setattr("api.media._tmdb.search_movie", stub)

    r = await authed_client.get("/api/media/tmdb/search/movie", params={"q": "matrix", "year": 1999})

    assert r.status_code == 200
    assert r.json() == {"results": [{"id": 603}]}
    assert stub.call_args.args[0] == "matrix"
    assert stub.call_args.kwargs == {"language": None, "year": 1999}


@pytest.mark.asyncio
async def test_tmdb_search_tv_route_forwards_query(authed_client, monkeypatch):
    stub = AsyncMock(return_value={"results": []})
    monkeypatch.setattr("api.media._tmdb.search_tv", stub)

    r = await authed_client.get("/api/media/tmdb/search/tv", params={"q": "dexter", "language": "en"})

    assert r.status_code == 200
    assert stub.call_args.args[0] == "dexter"
    assert stub.call_args.kwargs == {"language": "en", "year": None}


@pytest.mark.asyncio
async def test_tmdb_seasons_route_forwards_path_and_language(authed_client, monkeypatch):
    stub = AsyncMock(return_value={"seasons": []})
    monkeypatch.setattr("api.media._tmdb.get_tv_seasons", stub)

    r = await authed_client.get("/api/media/tmdb/tv/42/seasons", params={"language": "en"})

    assert r.status_code == 200
    assert stub.call_args.args[0] == 42
    assert stub.call_args.kwargs == {"language": "en"}


@pytest.mark.asyncio
async def test_tmdb_episodes_route_forwards_path(authed_client, monkeypatch):
    stub = AsyncMock(return_value={"episodes": []})
    monkeypatch.setattr("api.media._tmdb.get_season_episodes", stub)

    r = await authed_client.get("/api/media/tmdb/tv/42/season/2")

    assert r.status_code == 200
    assert stub.call_args.args[0] == 42
    assert stub.call_args.args[1] == 2
    assert stub.call_args.kwargs == {"language": None}


@pytest.mark.asyncio
async def test_tmdb_detail_route_threads_viewer_locale(authed_client, monkeypatch):
    stub = AsyncMock(return_value={"id": 603, "title": "The Matrix"})
    monkeypatch.setattr("api.media._tmdb.get_media_detail", stub)

    r = await authed_client.get(
        "/api/media/tmdb/detail/movie/603",
        headers={"X-MK-Locale": "en"},
    )

    assert r.status_code == 200
    assert stub.call_args.args[0] == "movie"
    assert stub.call_args.args[1] == 603
    assert stub.call_args.kwargs == {"locale": "en"}


@pytest.mark.asyncio
async def test_tmdb_detail_route_rejects_unknown_media_type(authed_client):
    # Route-level guard, distinct from the service-level failure tests.
    r = await authed_client.get("/api/media/tmdb/detail/book/1")

    assert r.status_code == 200
    assert r.json() == {"error": "invalid_media_type"}


@pytest.mark.asyncio
async def test_media_route_requires_authentication(client):
    # No login → the get_current_user dependency must reject the request.
    r = await client.get("/api/media/tmdb/search/movie", params={"q": "x"})

    assert r.status_code == 401


# --- Browse / listing routes (api/media/_browse.py) -------------------------


@pytest.mark.asyncio
async def test_rootpath_route_returns_configured_path(authed_client, monkeypatch):
    monkeypatch.setattr("api.media._browse.MEDIA_FOLDERS", {"movies": "/data/movies"})

    r = await authed_client.get("/api/media/rootpath/movies")

    assert r.status_code == 200
    assert r.json() == {"path": "/data/movies", "key": "movies"}


@pytest.mark.asyncio
async def test_browse_dirs_root_returns_browse_roots(authed_client, monkeypatch):
    roots = [{"name": "movies", "path": "/data/movies"}]
    monkeypatch.setattr("api.media._browse._get_browse_roots", lambda: roots)

    r = await authed_client.get("/api/media/browse-dirs", params={"path": "/"})

    assert r.status_code == 200
    assert r.json() == {"path": "/", "dirs": roots}


@pytest.mark.asyncio
async def test_browse_dirs_lists_visible_subdirs(authed_client, monkeypatch, tmp_path):
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / ".hidden").mkdir()  # dot-prefixed → filtered out
    (tmp_path / "note.txt").write_text("x")  # file → not a directory

    monkeypatch.setattr(
        "api.media._browse._get_browse_roots",
        lambda: [{"name": tmp_path.name, "path": str(tmp_path)}],
    )

    r = await authed_client.get("/api/media/browse-dirs", params={"path": str(tmp_path)})

    assert r.status_code == 200
    names = {d["name"] for d in r.json()["dirs"]}
    assert names == {"alpha", "beta"}


@pytest.mark.asyncio
async def test_files_route_forwards_folder_and_subpath(authed_client, monkeypatch):
    stub = AsyncMock(return_value={"path": "movies/season1", "items": []})
    monkeypatch.setattr("api.media._browse.list_files", stub)

    r = await authed_client.get("/api/media/files/movies", params={"subpath": "season1"})

    assert r.status_code == 200
    assert r.json() == {"path": "movies/season1", "items": []}
    assert stub.call_args.args == ("movies", "season1")


# --- Metadata route (api/media/_metadata.py) --------------------------------


@pytest.mark.asyncio
async def test_metadata_route_assembles_track_lists(authed_client, monkeypatch, tmp_path):
    media_file = tmp_path / "movie.mkv"
    media_file.write_bytes(b"x")
    monkeypatch.setattr("api.media._metadata._ensure_within_media_roots", lambda _p: media_file)

    probe = AsyncMock(return_value=(
        {
            "format": {"size": "1048576", "duration": "3661.0", "bit_rate": "128000"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "bit_rate": "5000000"},
                {"codec_type": "audio", "codec_name": "aac", "channels": 6, "tags": {"language": "eng"}},
            ],
        },
        None,
    ))
    monkeypatch.setattr("api.media._metadata._run_ffprobe", probe)

    r = await authed_client.get("/api/media/metadata", params={"path": str(media_file)})

    assert r.status_code == 200
    body = r.json()
    assert len(body["pistes_video"]) == 1
    assert len(body["pistes_audio"]) == 1
    assert body["pistes_sous_titres"] == []
    assert body["duree"] == "1h 01m 01s"


@pytest.mark.asyncio
async def test_metadata_route_reports_missing_file(authed_client, monkeypatch, tmp_path):
    # Guard passes (returns a Path) but the file does not exist on disk.
    missing = tmp_path / "ghost.mkv"
    monkeypatch.setattr("api.media._metadata._ensure_within_media_roots", lambda _p: missing)

    r = await authed_client.get("/api/media/metadata", params={"path": str(missing)})

    assert r.status_code == 200
    assert r.json() == {"error": "file_not_found"}
