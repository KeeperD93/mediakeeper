"""Typed sub-models for the subtitle batch payloads (#137).

``operations`` / ``items`` were ``list[dict]`` (free-form, no inner
validation). They are now ``list[<typed sub-model>]`` so a malformed inner
object (unknown key, wrong type) is rejected up front. The routes still hand
plain dicts to the unchanged services: batch-remove reads scalars by
attribute, batch-download / available-count ``model_dump()`` at the boundary.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from api.subtitles._schemas import (
    AvailableCountRequest,
    BatchDownloadRequest,
    BatchRemoveStreamRequest,
)


def test_batch_remove_operation_validates_inner_object():
    BatchRemoveStreamRequest(operations=[{"item_id": "i", "stream_index": 1}])
    with pytest.raises(ValidationError):  # unknown inner key
        BatchRemoveStreamRequest(operations=[{"item_id": "i", "stream_index": 1, "evil": True}])
    with pytest.raises(ValidationError):  # wrong inner type
        BatchRemoveStreamRequest(operations=[{"item_id": "i", "stream_index": "abc"}])
    with pytest.raises(ValidationError):  # missing required inner field
        BatchRemoveStreamRequest(operations=[{"item_id": "i"}])


def test_batch_download_item_validates_inner_object():
    BatchDownloadRequest(items=[{"imdb_id": "tt1"}])  # optional fields default
    BatchDownloadRequest(items=[])
    with pytest.raises(ValidationError):  # unknown inner key
        BatchDownloadRequest(items=[{"imdb_id": "tt1", "evil": True}])
    with pytest.raises(ValidationError):  # wrong inner type (season is int)
        BatchDownloadRequest(items=[{"season": "not-an-int"}])


def test_available_count_item_validates_inner_object():
    AvailableCountRequest(items=[{"imdb_id": "tt1", "tmdb_id": "42", "type": "Movie"}])
    AvailableCountRequest(items=[{}])  # all fields optional
    with pytest.raises(ValidationError):  # unknown inner key
        AvailableCountRequest(items=[{"imdb_id": "tt1", "evil": True}])


@pytest.mark.asyncio
async def test_batch_remove_streams_route_reads_operations_by_attribute(authed_client):
    """The route migrated from op.get(...) to op.item_id / op.stream_index;
    a valid typed operation must still flow through to remove_stream."""
    with patch(
        "api.subtitles._discovery.remove_stream",
        new=AsyncMock(return_value={"success": True}),
    ):
        r = await authed_client.post(
            "/api/subtitles/batch-remove-streams",
            json={"operations": [{"item_id": "abc", "stream_index": 2}]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] == [{"item_id": "abc", "stream_index": 2}]
    assert body["failed"] == []


@pytest.mark.asyncio
async def test_batch_remove_streams_groups_by_item(authed_client):
    """Ops run grouped by item (groups concurrent, same-item ops serialised);
    every op is reported once and same-item ops keep their submitted order."""
    calls = []

    async def fake_remove(db, item_id, stream_index):
        calls.append((item_id, stream_index))
        return {"success": True}

    with patch("api.subtitles._discovery.remove_stream", new=fake_remove):
        r = await authed_client.post(
            "/api/subtitles/batch-remove-streams",
            json={"operations": [
                {"item_id": "a", "stream_index": 1},
                {"item_id": "b", "stream_index": 2},
                {"item_id": "a", "stream_index": 3},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == []
    assert {(s["item_id"], s["stream_index"]) for s in body["success"]} == {
        ("a", 1), ("b", 2), ("a", 3),
    }
    # Same-item ops stay serialised in submitted order within their group.
    assert [idx for (iid, idx) in calls if iid == "a"] == [1, 3]


@pytest.mark.asyncio
async def test_available_count_route_dumps_typed_items_to_service(authed_client):
    """The route model_dump()s the typed items, so the unchanged service
    still receives plain dicts (not Pydantic models)."""
    captured = {}

    async def fake_counts(db, items):
        captured["items"] = items
        return {"counts": {}}

    with patch("api.subtitles._discovery.get_available_counts", new=fake_counts):
        r = await authed_client.post(
            "/api/subtitles/available-count",
            json={"items": [{"imdb_id": "tt1", "tmdb_id": "42", "type": "Movie"}]},
        )
    assert r.status_code == 200
    assert captured["items"] == [{"imdb_id": "tt1", "tmdb_id": "42", "type": "Movie"}]
