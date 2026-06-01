"""TMDB rating backfill for the home "Recently added on Emby" row.

``_backfill_tmdb_votes`` fills ``vote`` only on items whose Emby payload
carries no CommunityRating (vote falsy), leaves items that already have a
rating untouched, and skips items without a tmdb_id. ``get_meta_cached`` is
mocked — the helper imports it lazily from ``services.tmdb``.
"""
from unittest.mock import AsyncMock

import pytest

import services.tmdb as tmdb_mod
from services.portal.available import _backfill_tmdb_votes


@pytest.mark.asyncio
async def test_backfill_fills_only_missing_votes(monkeypatch):
    monkeypatch.setattr(
        tmdb_mod, "get_meta_cached",
        AsyncMock(return_value={"runtime": 90, "year": "2024", "vote": 7.7}),
    )
    items = [
        {"tmdb_id": 5, "media_type": "movie", "vote": 0},      # no Emby rating → fill
        {"tmdb_id": 6, "media_type": "movie", "vote": 8.2},    # has rating → keep
        {"media_type": "movie", "vote": 0},                    # no tmdb_id → skip
    ]
    await _backfill_tmdb_votes(items, None)

    assert items[0]["vote"] == 7.7   # filled from TMDB
    assert items[1]["vote"] == 8.2   # untouched
    assert items[2]["vote"] == 0     # skipped (no tmdb_id)


@pytest.mark.asyncio
async def test_backfill_skips_when_tmdb_has_no_vote(monkeypatch):
    monkeypatch.setattr(
        tmdb_mod, "get_meta_cached",
        AsyncMock(return_value={"runtime": 90, "year": "2024", "vote": 0}),
    )
    items = [{"tmdb_id": 5, "media_type": "movie", "vote": 0}]
    await _backfill_tmdb_votes(items, None)

    assert items[0]["vote"] == 0  # TMDB had no rating either → left as-is
