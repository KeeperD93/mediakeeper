"""Bounds on admin/internal write surfaces (#383): oversized, negative or
out-of-domain input is rejected at validation time (422) instead of
crashing the request or being stored unbounded. Endpoints sit behind the
backoffice auth, so this is defence-in-depth, not a public guard.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.duplicates import CleanupEntry, CleanupRequest
from api.duplicates import IgnoreRequest as DupIgnoreRequest
from api.media._release_tags import ReleaseTagsPayload
from api.portal.auth import PortalLoginRequest
from api.portal.requests import BatchStatusQuery, CreateRequest, StatusUpdate
from api.portal.tickets import CreateTicket, TicketReplyBody, TicketStatusUpdate
from api.portal.xp_events import XpEventPayload, XpEventUpdate
from api.scheduler import TaskUpdateRequest
from api.security import BlockRequest
from api.settings import (
    MediaFolderRequest, MediaFoldersSaveRequest, NetworkSettingsRequest, ToolSaveRequest,
)
from api.stats._exclusions import ExclusionRequest
from api.stats._users import MergeRequest
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


def test_dup_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        DupIgnoreRequest(keys=["k"], bogus=1)
    with pytest.raises(ValidationError):
        CleanupEntry(title="t", bogus=1)
    with pytest.raises(ValidationError):
        CleanupRequest(entries=[], bogus=1)


def test_stats_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        MergeRequest(target_user_id="u1", bogus=1)
    with pytest.raises(ValidationError):
        ExclusionRequest(mode="exact", value="x", bogus=1)


def test_release_tags_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ReleaseTagsPayload(tags=["1080p"], bogus=1)


def test_request_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        CreateRequest(tmdb_id=1, media_type="movie", title="X", bogus=1)
    with pytest.raises(ValidationError):
        StatusUpdate(status="approved", bogus=1)
    with pytest.raises(ValidationError):
        BatchStatusQuery(tmdb_ids=[1], bogus=1)


def test_ticket_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        CreateTicket(
            media_title="X", media_type="other", issue_type="audio",
            description="d", bogus=1,
        )
    with pytest.raises(ValidationError):
        TicketReplyBody(content="hi", bogus=1)
    with pytest.raises(ValidationError):
        TicketStatusUpdate(status="open", bogus=1)


def test_xp_event_schemas_reject_unknown_fields():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        XpEventPayload(name="X", starts_at=now, ends_at=now, bogus=1)
    with pytest.raises(ValidationError):
        XpEventUpdate(name="X", bogus=1)


def test_settings_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        ToolSaveRequest(enabled=True, bogus=1)
    with pytest.raises(ValidationError):
        MediaFolderRequest(label="Movies", path="/data/movies", bogus=1)
    with pytest.raises(ValidationError):
        MediaFoldersSaveRequest(folders=[], bogus=1)
    with pytest.raises(ValidationError):
        NetworkSettingsRequest(image_cache_enabled=True, bogus=1)


def test_security_auth_scheduler_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        BlockRequest(username="x", bogus=1)
    with pytest.raises(ValidationError):
        TaskUpdateRequest(enabled=True, bogus=1)
    with pytest.raises(ValidationError):
        PortalLoginRequest(username="u", password="p", bogus=1)


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
