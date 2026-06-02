"""Route-handler coverage for /api/media/{preview,rename,rename-batch,build/*,rename-folder}.

The six rename endpoints were only exercised through the service layer
(``apply_rename`` in ``test_media_manager.py``). The HTTP contract was never
pinned: that the strict ``extra="forbid"`` schemas reject unknown fields and
oversized/out-of-range values with 422, and that each route forwards the
service output verbatim. Without these, a schema loosening or a route↔service
wiring regression would pass CI unnoticed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

_ADMIN_PASSWORD = "TestPassword123!"


@pytest_asyncio.fixture
async def authed_client(client, admin_user):
    """``client`` logged in as the local backoffice admin.

    The default ``client`` fixture auto-seeds the CSRF cookie+header and
    re-syncs it across the auth-boundary rotation. The rename routes sit
    behind ``get_current_user`` + the CSRF middleware, so this is the only
    fixture that authenticates them.
    """
    r = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": _ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return client


# /api/media/preview


@pytest.mark.asyncio
async def test_preview_forwards_service_output(authed_client):
    with patch(
        "api.media._rename.preview_rename",
        new=Mock(return_value={"old_path": "/m/a.mkv", "new_name": "b.mkv"}),
    ):
        r = await authed_client.post(
            "/api/media/preview",
            json={"old_path": "/m/a.mkv", "new_name": "b.mkv"},
        )
    assert r.status_code == 200
    assert r.json() == {"old_path": "/m/a.mkv", "new_name": "b.mkv"}


@pytest.mark.asyncio
async def test_preview_rejects_extra_field(authed_client):
    r = await authed_client.post(
        "/api/media/preview",
        json={"old_path": "/m/a.mkv", "new_name": "b.mkv", "evil": "x"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_preview_rejects_oversized_new_name(authed_client):
    r = await authed_client.post(
        "/api/media/preview",
        json={"old_path": "/m/a.mkv", "new_name": "x" * 256},
    )
    assert r.status_code == 422


# /api/media/rename


@pytest.mark.asyncio
async def test_rename_forwards_service_success(authed_client):
    with patch(
        "api.media._rename.apply_rename",
        new=AsyncMock(return_value={"success": True, "new_path": "/m/b.mkv"}),
    ):
        r = await authed_client.post(
            "/api/media/rename",
            json={"old_path": "/m/a.mkv", "new_name": "b.mkv"},
        )
    assert r.status_code == 200
    assert r.json() == {"success": True, "new_path": "/m/b.mkv"}


@pytest.mark.asyncio
async def test_rename_keeps_soft_error_in_200_body(authed_client):
    """A soft service error stays in the 200 body — the rename route does not
    promote it to a 500 (unlike the move routes)."""
    with patch(
        "api.media._rename.apply_rename",
        new=AsyncMock(return_value={"error": "path_not_allowed"}),
    ):
        r = await authed_client.post(
            "/api/media/rename",
            json={"old_path": "/m/a.mkv", "new_name": "b.mkv"},
        )
    assert r.status_code == 200
    assert r.json() == {"error": "path_not_allowed"}


@pytest.mark.asyncio
async def test_rename_rejects_empty_new_name(authed_client):
    r = await authed_client.post(
        "/api/media/rename",
        json={"old_path": "/m/a.mkv", "new_name": ""},
    )
    assert r.status_code == 422


# /api/media/rename-batch


@pytest.mark.asyncio
async def test_rename_batch_forwards_service_output(authed_client):
    with patch(
        "api.media._rename.apply_rename_batch",
        new=AsyncMock(return_value=[{"success": True}, {"error": "path_not_allowed"}]),
    ):
        r = await authed_client.post(
            "/api/media/rename-batch",
            json={
                "items": [
                    {"old_path": "/m/a.mkv", "new_name": "b.mkv"},
                    {"old_path": "/m/c.mkv", "new_name": "d.mkv"},
                ],
                "cat": "films",
            },
        )
    assert r.status_code == 200
    assert r.json() == [{"success": True}, {"error": "path_not_allowed"}]


@pytest.mark.asyncio
async def test_rename_batch_rejects_extra_field_in_item(authed_client):
    r = await authed_client.post(
        "/api/media/rename-batch",
        json={"items": [{"old_path": "/m/a.mkv", "new_name": "b.mkv", "evil": "x"}]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_rename_batch_rejects_too_many_items(authed_client):
    items = [{"old_path": f"/m/{i}.mkv", "new_name": f"{i}.mkv"} for i in range(501)]
    r = await authed_client.post("/api/media/rename-batch", json={"items": items})
    assert r.status_code == 422


# /api/media/build/movie


@pytest.mark.asyncio
async def test_build_movie_wraps_service_name(authed_client):
    with patch("api.media._rename.build_movie_name", new=Mock(return_value="Movie (2024).mkv")):
        r = await authed_client.post(
            "/api/media/build/movie",
            json={"title": "Movie", "year": "2024", "quality": "1080p", "ext": "mkv"},
        )
    assert r.status_code == 200
    assert r.json() == {"name": "Movie (2024).mkv"}


@pytest.mark.asyncio
async def test_build_movie_rejects_missing_title(authed_client):
    r = await authed_client.post("/api/media/build/movie", json={"year": "2024"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_build_movie_rejects_extra_field(authed_client):
    r = await authed_client.post(
        "/api/media/build/movie",
        json={"title": "Movie", "evil": "x"},
    )
    assert r.status_code == 422


# /api/media/build/episode


@pytest.mark.asyncio
async def test_build_episode_wraps_service_name(authed_client):
    with patch("api.media._rename.build_episode_name", new=Mock(return_value="Show S01E02.mkv")):
        r = await authed_client.post(
            "/api/media/build/episode",
            json={"series": "Show", "season": 1, "episode": 2, "title": "Pilot", "ext": "mkv"},
        )
    assert r.status_code == 200
    assert r.json() == {"name": "Show S01E02.mkv"}


@pytest.mark.asyncio
async def test_build_episode_rejects_out_of_range_season(authed_client):
    r = await authed_client.post(
        "/api/media/build/episode",
        json={"series": "Show", "season": 1000, "episode": 2, "title": "Pilot"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_build_episode_rejects_extra_field(authed_client):
    r = await authed_client.post(
        "/api/media/build/episode",
        json={"series": "Show", "season": 1, "episode": 2, "title": "Pilot", "evil": "x"},
    )
    assert r.status_code == 422


# /api/media/rename-folder


@pytest.mark.asyncio
async def test_rename_folder_unknown_category_returns_soft_error(authed_client):
    with patch("api.media._rename.MEDIA_FOLDERS", {"telechargement": "/media/dl"}):
        r = await authed_client.post(
            "/api/media/rename-folder",
            json={"cat": "bogus", "subpath": "old", "new_name": "new"},
        )
    assert r.status_code == 200
    assert r.json() == {"error": "Unknown category: bogus"}


@pytest.mark.asyncio
async def test_rename_folder_forwards_service_output(authed_client):
    with patch("api.media._rename.MEDIA_FOLDERS", {"telechargement": "/media/dl"}), \
         patch("api.media._rename._validate_path", new=Mock(return_value=None)), \
         patch(
             "api.media._rename.apply_rename_batch",
             new=AsyncMock(return_value=[{"success": True, "new_path": "/media/dl/new"}]),
         ):
        r = await authed_client.post(
            "/api/media/rename-folder",
            json={"cat": "telechargement", "subpath": "old", "new_name": "new"},
        )
    assert r.status_code == 200
    assert r.json() == {"success": True, "new_path": "/media/dl/new"}


@pytest.mark.asyncio
async def test_rename_folder_rejects_extra_field(authed_client):
    r = await authed_client.post(
        "/api/media/rename-folder",
        json={"cat": "telechargement", "subpath": "old", "new_name": "new", "evil": "x"},
    )
    assert r.status_code == 422
