"""Tests for the Top 20 runtime + year enrichment helper.

`_enrich_top20_meta` stamps runtime + year on each item that carries a
tmdb_id, leaves the others alone, and isolates per-item TMDB failures
so one bad item never kills the whole payload.
"""
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.portal.top20 import _enrich_top20_meta


@pytest.fixture
def fake_db():
    """Sentinel passed through — the helper only forwards it to
    `get_meta_cached`, which we mock out entirely."""
    return MagicMock(name="fake_db")


# ── Cases ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_item_with_tmdb_id_gets_runtime_and_year_stamped(fake_db):
    """A fully-described item picks up runtime + year from the cache."""
    items = [
        {"tmdb_id": 99, "media_type": "movie", "title": "A"},
    ]
    fake_meta = AsyncMock(return_value={"runtime": 90, "year": "2025"})
    with patch("api.portal.top20.get_meta_cached", new=fake_meta):
        await _enrich_top20_meta(items, fake_db)
    assert items[0]["runtime"] == 90
    assert items[0]["year"] == "2025"
    fake_meta.assert_awaited_once_with(99, "movie", fake_db)


@pytest.mark.asyncio
async def test_item_without_tmdb_id_is_left_untouched(fake_db):
    """Items missing tmdb_id (or media_type) skip the lookup entirely."""
    items = [
        {"title": "No tmdb"},
        {"tmdb_id": 100, "title": "No media_type"},
        {"media_type": "tv", "title": "No tmdb id"},
    ]
    fake_meta = AsyncMock(return_value={"runtime": 90, "year": "2025"})
    with patch("api.portal.top20.get_meta_cached", new=fake_meta):
        await _enrich_top20_meta(items, fake_db)
    for it in items:
        assert "runtime" not in it
        assert "year" not in it
    fake_meta.assert_not_awaited()


@pytest.mark.asyncio
async def test_one_item_failure_does_not_break_others(fake_db, caplog):
    """A single TMDB hiccup is logged but the rest of the payload still
    gets enriched. Validates the per-item try/except contract."""
    items = [
        {"tmdb_id": 1, "media_type": "movie", "title": "First"},
        {"tmdb_id": 2, "media_type": "movie", "title": "Boom"},
        {"tmdb_id": 3, "media_type": "tv", "title": "Third"},
    ]

    async def fake_meta(tid, mtype, db):
        if tid == 2:
            raise RuntimeError("boom")
        if tid == 1:
            return {"runtime": 95, "year": "2020"}
        return {"runtime": 45, "year": "2021"}

    caplog.set_level(logging.WARNING, logger="mediakeeper.portal.top20")
    with patch("api.portal.top20.get_meta_cached", new=fake_meta):
        await _enrich_top20_meta(items, fake_db)

    # 1 and 3 enrich normally
    assert items[0]["runtime"] == 95
    assert items[0]["year"] == "2020"
    assert items[2]["runtime"] == 45
    assert items[2]["year"] == "2021"
    # 2 stays untouched and a warning was logged
    assert "runtime" not in items[1]
    assert "year" not in items[1]
    assert any("meta enrich failed" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_partial_meta_only_stamps_present_fields(fake_db):
    """An empty / partial cache payload must not introduce blank fields."""
    items = [
        {"tmdb_id": 10, "media_type": "movie", "title": "A"},
        {"tmdb_id": 11, "media_type": "movie", "title": "B"},
    ]

    async def fake_meta(tid, mtype, db):
        if tid == 10:
            return {"runtime": 80, "year": ""}  # year missing
        return {"runtime": 0, "year": "2021"}  # runtime missing

    with patch("api.portal.top20.get_meta_cached", new=fake_meta):
        await _enrich_top20_meta(items, fake_db)

    assert items[0]["runtime"] == 80
    assert "year" not in items[0]
    assert "runtime" not in items[1]
    assert items[1]["year"] == "2021"
