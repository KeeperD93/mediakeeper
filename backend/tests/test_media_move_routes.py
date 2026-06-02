"""Route-handler coverage for /api/media/{move,delete,create-folders,...}.

Every endpoint must:

* propagate a service-layer success payload as 200 OK,
* keep soft validation outcomes (path_not_allowed, source_not_found, ...)
  in the 200 OK body so the frontend can surface them as user feedback,
* promote a hard runtime failure code (listed in
  :data:`services.media_manager._errors.HARD_FAIL_CODES`) to a 500
  HTTPException with the code in ``detail``.

These contracts were not pinned before the cycle 18.b refactor and a
silent regression to the previous ``return {"error": str(exc)}`` pattern
would re-introduce the CodeQL ``py/stack-trace-exposure`` finding.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# /api/media/move


@pytest.mark.asyncio
async def test_move_success_returns_200(authed_client):
    with patch(
        "api.media._move.move_file",
        new=AsyncMock(return_value={"success": True, "src": "/a/x.mkv", "dest": "/b"}),
    ):
        r = await authed_client.post(
            "/api/media/move",
            json={"src_path": "/a/x.mkv", "dest_folder": "/b"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "error" not in body


@pytest.mark.asyncio
async def test_move_soft_error_returns_200_with_body(authed_client):
    with patch(
        "api.media._move.move_file",
        new=AsyncMock(return_value={"error": "path_not_allowed"}),
    ):
        r = await authed_client.post(
            "/api/media/move",
            json={"src_path": "/a/x.mkv", "dest_folder": "/b"},
        )
    assert r.status_code == 200
    assert r.json() == {"error": "path_not_allowed"}


@pytest.mark.asyncio
async def test_move_hard_fail_returns_500(authed_client):
    with patch(
        "api.media._move.move_file",
        new=AsyncMock(return_value={"error": "move_failed"}),
    ):
        r = await authed_client.post(
            "/api/media/move",
            json={"src_path": "/a/x.mkv", "dest_folder": "/b"},
        )
    assert r.status_code == 500
    assert r.json() == {"detail": "move_failed"}


# /api/media/move-cat


@pytest.mark.asyncio
async def test_move_cat_unknown_destination_returns_200(authed_client):
    """An invalid ``dest_cat`` is a soft error: 200 + body with code."""
    r = await authed_client.post(
        "/api/media/move-cat",
        json={"src_path": "/a/x.mkv", "src_cat": "Films", "dest_cat": "BogusCat"},
    )
    assert r.status_code == 200
    assert r.json() == {"error": "unknown_destination_category"}


@pytest.mark.asyncio
async def test_move_cat_hard_fail_returns_500(authed_client):
    with patch(
        "api.media._move.MEDIA_FOLDERS",
        {"Films": "/media/films", "Series": "/media/series"},
    ), patch(
        "api.media._move.move_file",
        new=AsyncMock(return_value={"error": "move_failed"}),
    ):
        r = await authed_client.post(
            "/api/media/move-cat",
            json={"src_path": "/a/x.mkv", "src_cat": "Films", "dest_cat": "Series"},
        )
    assert r.status_code == 500
    assert r.json() == {"detail": "move_failed"}


@pytest.mark.asyncio
async def test_move_cat_success_returns_200(authed_client):
    with patch(
        "api.media._move.MEDIA_FOLDERS",
        {"Films": "/media/films", "Series": "/media/series"},
    ), patch(
        "api.media._move.move_file",
        new=AsyncMock(return_value={"success": True, "src": "/a/x.mkv", "dest": "/media/series"}),
    ):
        r = await authed_client.post(
            "/api/media/move-cat",
            json={"src_path": "/a/x.mkv", "src_cat": "Films", "dest_cat": "Series"},
        )
    assert r.status_code == 200
    assert r.json()["success"] is True


# /api/media/delete


@pytest.mark.asyncio
async def test_delete_success_returns_200(authed_client):
    with patch(
        "api.media._move.delete_file",
        new=AsyncMock(return_value={"success": True}),
    ):
        r = await authed_client.post("/api/media/delete", json={"path": "/a/x.mkv"})
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_soft_error_returns_200(authed_client):
    with patch(
        "api.media._move.delete_file",
        new=AsyncMock(return_value={"error": "path_not_allowed"}),
    ):
        r = await authed_client.post("/api/media/delete", json={"path": "/a/x.mkv"})
    assert r.status_code == 200
    assert r.json() == {"error": "path_not_allowed"}


@pytest.mark.asyncio
async def test_delete_hard_fail_returns_500(authed_client):
    with patch(
        "api.media._move.delete_file",
        new=AsyncMock(return_value={"error": "delete_failed"}),
    ):
        r = await authed_client.post("/api/media/delete", json={"path": "/a/x.mkv"})
    assert r.status_code == 500
    assert r.json() == {"detail": "delete_failed"}


# /api/media/delete-batch (per-item accumulator, never raises 500)


@pytest.mark.asyncio
async def test_delete_batch_aggregates_success_and_errors(authed_client):
    """delete-batch aggregates per-item results — even a hard delete_failed
    on one item stays in the response body, the route returns 200 with the
    error count surfaced in the payload."""
    side_effect = [
        {"success": True},
        {"error": "delete_failed"},
        {"error": "path_not_allowed"},
    ]
    with patch(
        "api.media._move.delete_file",
        new=AsyncMock(side_effect=side_effect),
    ):
        r = await authed_client.post(
            "/api/media/delete-batch",
            json={"paths": ["/a", "/b", "/c"]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] == 1
    assert body["errors"] == 2
    assert len(body["results"]) == 3


# /api/media/create-folders (uniform dict contract: {"results": [...]})


@pytest.mark.asyncio
async def test_create_folders_success_returns_200_with_results(authed_client):
    with patch(
        "api.media._move.create_folders_batch",
        new=AsyncMock(return_value={"results": [
            {"parent_path": "/m", "folder_name": "Season 01", "success": True, "path": "/m/Season 01", "already_existed": False},
        ]}),
    ):
        r = await authed_client.post(
            "/api/media/create-folders",
            json={"folders": [{"parent_path": "/m", "folder_name": "Season 01"}]},
        )
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert body["results"][0]["success"] is True


@pytest.mark.asyncio
async def test_create_folders_item_error_returns_200(authed_client):
    """An item-level soft error stays in results — no 500."""
    with patch(
        "api.media._move.create_folders_batch",
        new=AsyncMock(return_value={"results": [
            {"parent_path": "/m", "folder_name": "..bad", "error": "path_not_allowed"},
        ]}),
    ):
        r = await authed_client.post(
            "/api/media/create-folders",
            json={"folders": [{"parent_path": "/m", "folder_name": "..bad"}]},
        )
    assert r.status_code == 200
    assert r.json()["results"][0]["error"] == "path_not_allowed"


@pytest.mark.asyncio
async def test_create_folders_batch_hard_fail_returns_500(authed_client):
    """Batch-level hard fail (unexpected exception escaped the loop) → 500."""
    with patch(
        "api.media._move.create_folders_batch",
        new=AsyncMock(return_value={"error": "create_folders_failed", "results": []}),
    ):
        r = await authed_client.post(
            "/api/media/create-folders",
            json={"folders": [{"parent_path": "/m", "folder_name": "x"}]},
        )
    assert r.status_code == 500
    assert r.json() == {"detail": "create_folders_failed"}


# /api/media/check-move-conflicts


@pytest.mark.asyncio
async def test_check_conflicts_success_returns_200(authed_client):
    with patch(
        "api.media._move.check_move_conflicts",
        new=AsyncMock(return_value={"conflicts": []}),
    ):
        r = await authed_client.post(
            "/api/media/check-move-conflicts",
            json={"file_names": ["a.mkv"], "dest_folder": "/b"},
        )
    assert r.status_code == 200
    assert r.json() == {"conflicts": []}


@pytest.mark.asyncio
async def test_check_conflicts_soft_error_returns_200(authed_client):
    with patch(
        "api.media._move.check_move_conflicts",
        new=AsyncMock(return_value={"error": "path_not_allowed"}),
    ):
        r = await authed_client.post(
            "/api/media/check-move-conflicts",
            json={"file_names": ["a.mkv"], "dest_folder": "/b"},
        )
    assert r.status_code == 200
    assert r.json() == {"error": "path_not_allowed"}


@pytest.mark.asyncio
async def test_check_conflicts_hard_fail_returns_500(authed_client):
    with patch(
        "api.media._move.check_move_conflicts",
        new=AsyncMock(return_value={"error": "check_conflicts_failed"}),
    ):
        r = await authed_client.post(
            "/api/media/check-move-conflicts",
            json={"file_names": ["a.mkv"], "dest_folder": "/b"},
        )
    assert r.status_code == 500
    assert r.json() == {"detail": "check_conflicts_failed"}


# /api/media/move-overwrite


@pytest.mark.asyncio
async def test_move_overwrite_success_returns_200(authed_client):
    with patch(
        "api.media._move.move_file_overwrite",
        new=AsyncMock(return_value={"success": True, "overwritten": True, "src": "/a", "dest": "/b"}),
    ):
        r = await authed_client.post(
            "/api/media/move-overwrite",
            json={"src_path": "/a/x.mkv", "dest_folder": "/b"},
        )
    assert r.status_code == 200
    assert r.json()["overwritten"] is True


@pytest.mark.asyncio
async def test_move_overwrite_soft_error_returns_200(authed_client):
    with patch(
        "api.media._move.move_file_overwrite",
        new=AsyncMock(return_value={"error": "path_not_allowed"}),
    ):
        r = await authed_client.post(
            "/api/media/move-overwrite",
            json={"src_path": "/a/x.mkv", "dest_folder": "/b"},
        )
    assert r.status_code == 200
    assert r.json() == {"error": "path_not_allowed"}


@pytest.mark.asyncio
async def test_move_overwrite_hard_fail_returns_500(authed_client):
    with patch(
        "api.media._move.move_file_overwrite",
        new=AsyncMock(return_value={"error": "move_overwrite_failed"}),
    ):
        r = await authed_client.post(
            "/api/media/move-overwrite",
            json={"src_path": "/a/x.mkv", "dest_folder": "/b"},
        )
    assert r.status_code == 500
    assert r.json() == {"detail": "move_overwrite_failed"}
