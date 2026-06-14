"""Bounds on collection inputs (#384): oversized lists are rejected at
validation time instead of being processed unbounded, and the availability
fan-out is capped so a large batch can't saturate Emby + TMDB.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

import api.portal.availability as availability
from api.media._move import BatchDeleteRequest
from api.portal.availability import AvailabilityQuery
from api.portal._events_rooms import CreateMKEvent, MKEventMedia
from api.portal.lists import ItemsMove, ItemsRemove
from api.portal.requests import CreateRequest
from api.portal.tickets import CreateTicket


# --- Pydantic list-length bounds (no auth needed) ---

def test_availability_query_caps_items():
    with pytest.raises(ValidationError):
        AvailabilityQuery(items=[{"tmdb_id": i} for i in range(501)])


def test_batch_delete_caps_paths():
    with pytest.raises(ValidationError):
        BatchDeleteRequest(paths=["x"] * 1001)


def test_items_remove_caps_lists():
    with pytest.raises(ValidationError):
        ItemsRemove(item_ids=list(range(201)))


def test_items_move_caps_item_ids():
    with pytest.raises(ValidationError):
        ItemsMove(dst_list_id=1, item_ids=list(range(201)))


def test_create_request_caps_requested_seasons():
    with pytest.raises(ValidationError):
        CreateRequest(
            tmdb_id=1, media_type="movie", title="t",
            requested_seasons=list(range(101)),
        )


def test_create_event_caps_invitees():
    with pytest.raises(ValidationError):
        CreateMKEvent(
            title="t", kind="private",
            tmdb_ids=[MKEventMedia(tmdb_id=1, media_type="movie", title="x")],
            scheduled_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            invitees=list(range(101)),
        )


def test_create_ticket_caps_selected_seasons():
    with pytest.raises(ValidationError):
        CreateTicket(
            media_title="t", media_type="series", series_emby_id="s1",
            issue_type="other", description="d",
            selected_seasons=[{} for _ in range(101)],
        )


# --- Availability fan-out concurrency cap (the DoS guard) ---

@pytest.mark.asyncio
async def test_completeness_fan_out_is_concurrency_capped(monkeypatch):
    state = {"current": 0, "peak": 0}

    async def fake_check(db, emby_ids, tid, ignored_set):
        state["current"] += 1
        state["peak"] = max(state["peak"], state["current"])
        await asyncio.sleep(0.005)
        state["current"] -= 1
        return availability.AVAILABILITY_FULL

    monkeypatch.setattr(availability, "_check_series_completeness", fake_check)

    jobs = {i: [f"e{i}"] for i in range(40)}
    result = await availability._gather_tv_completeness(jobs, set())

    assert len(result) == 40
    assert all(v == availability.AVAILABILITY_FULL for v in result.values())
    assert state["peak"] <= availability._AVAILABILITY_CONCURRENCY
    assert state["peak"] > 1  # sanity: checks really ran in parallel
