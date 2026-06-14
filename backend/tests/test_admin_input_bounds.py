"""Bounds on admin/internal write surfaces (#383): oversized, negative or
out-of-domain input is rejected at validation time (422) instead of
crashing the request or being stored unbounded. Endpoints sit behind the
backoffice auth, so this is defence-in-depth, not a public guard.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.duplicates import CleanupEntry, CleanupRequest
from api.duplicates import IgnoreRequest as DupIgnoreRequest
from api.watchlist import IgnoreRequest as WlIgnoreRequest, TrackRequest, UntrackRequest


# --- Pydantic schema bounds (no auth needed) ---

def test_track_request_rejects_unknown_media_type():
    with pytest.raises(ValidationError):
        TrackRequest(tmdb_id=1, media_type="series")


def test_track_request_accepts_movie_and_tv():
    assert TrackRequest(tmdb_id=1, media_type="movie").media_type == "movie"
    assert TrackRequest(tmdb_id=2, media_type="tv").media_type == "tv"


def test_track_request_rejects_oversized_name():
    with pytest.raises(ValidationError):
        TrackRequest(tmdb_id=1, media_type="movie", name="x" * 501)


def test_track_request_rejects_negative_counts():
    with pytest.raises(ValidationError):
        TrackRequest(tmdb_id=1, media_type="movie", total_seasons=-1)


def test_untrack_request_rejects_unknown_media_type():
    with pytest.raises(ValidationError):
        UntrackRequest(tmdb_id=1, media_type="bogus")


def test_watchlist_ignore_request_caps_item_and_list():
    with pytest.raises(ValidationError):
        WlIgnoreRequest(keys=["x" * 513])
    with pytest.raises(ValidationError):
        WlIgnoreRequest(keys=["k"] * 1001)


def test_dup_ignore_request_caps_item_and_list():
    with pytest.raises(ValidationError):
        DupIgnoreRequest(keys=["x" * 513])
    with pytest.raises(ValidationError):
        DupIgnoreRequest(keys=["k"] * 1001)


def test_cleanup_entry_rejects_negative_size_and_oversized_fields():
    with pytest.raises(ValidationError):
        CleanupEntry(size_bytes=-1)
    with pytest.raises(ValidationError):
        CleanupEntry(action="a" * 33)
    with pytest.raises(ValidationError):
        CleanupEntry(title="t" * 513)


def test_cleanup_request_caps_entries():
    with pytest.raises(ValidationError):
        CleanupRequest(entries=[CleanupEntry() for _ in range(1001)])


# --- Route param bounds (Query / Path) via the authenticated client ---

@pytest.mark.asyncio
async def test_history_rejects_negative_limit(authed_client):
    r = await authed_client.get("/api/notifications/history?limit=-1")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_history_rejects_oversized_limit(authed_client):
    r = await authed_client.get("/api/notifications/history?limit=10000")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_history_accepts_in_range_limit(authed_client):
    r = await authed_client.get("/api/notifications/history?limit=50")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_alert_seen_rejects_oversized_id(authed_client):
    r = await authed_client.post("/api/alerts/seen/" + "x" * 200)
    assert r.status_code == 422
