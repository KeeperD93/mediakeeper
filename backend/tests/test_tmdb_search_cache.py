"""TTL cache + Emby cross-reference around :mod:`services.portal.tmdb_search`.

Pins the cache hit / miss accounting, the cross-ref freshness (admin
toggles must propagate without waiting for TTL), and the clear_cache
reset path.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal import tmdb_search


@pytest.fixture(autouse=True)
def _reset_cache():
    """Each test starts with a clean cache + zero counters."""
    tmdb_search.clear_cache()
    yield
    tmdb_search.clear_cache()


@pytest.mark.asyncio
async def test_search_caches_subsequent_calls(db_session):
    """First call hits TMDB, second call returns the cached payload."""
    fake_items = [
        {"tmdb_id": 1577, "media_type": "movie", "title": "Resident Evil"},
    ]
    with patch(
        "services.portal.tmdb_search.search_tmdb_multi",
        new=AsyncMock(return_value=fake_items),
    ) as mocked:
        first = await tmdb_search.search_with_cache(db_session, "resident")
        second = await tmdb_search.search_with_cache(db_session, "resident")

    assert mocked.call_count == 1
    assert [i["tmdb_id"] for i in first] == [1577]
    assert [i["tmdb_id"] for i in second] == [1577]

    stats = tmdb_search.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["keys"] == 1


@pytest.mark.asyncio
async def test_cache_keys_are_case_insensitive(db_session):
    """Query casing must not multiply cache entries."""
    with patch(
        "services.portal.tmdb_search.search_tmdb_multi",
        new=AsyncMock(return_value=[]),
    ) as mocked:
        await tmdb_search.search_with_cache(db_session, "Valkyrie")
        await tmdb_search.search_with_cache(db_session, "valkyrie")
        await tmdb_search.search_with_cache(db_session, "VALKYRIE")
    assert mocked.call_count == 1

    stats = tmdb_search.get_cache_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["keys"] == 1


@pytest.mark.asyncio
async def test_available_on_emby_flag_recomputed_on_cache_hit(db_session):
    """Admin imports a title — the next search must reflect it without TTL wait."""
    fake_items = [
        {"tmdb_id": 42, "media_type": "movie", "title": "Test"},
    ]
    with patch(
        "services.portal.tmdb_search.search_tmdb_multi",
        new=AsyncMock(return_value=fake_items),
    ):
        first = await tmdb_search.search_with_cache(db_session, "test")
        assert first[0]["available_on_emby"] is False

        # Admin "imports" the title into Emby — add an index row.
        db_session.add(
            EmbyTmdbIndex(
                emby_item_id="emby-42",
                tmdb_id=42,
                media_type="movie",
                title="Test",
            )
        )
        await db_session.commit()

        # Second call hits the cache for TMDB items but the Emby cross-ref
        # is recomputed, so the flag flips to True.
        second = await tmdb_search.search_with_cache(db_session, "test")
        assert second[0]["available_on_emby"] is True


@pytest.mark.asyncio
async def test_clear_cache_resets_counters_and_drops_entries(db_session):
    with patch(
        "services.portal.tmdb_search.search_tmdb_multi",
        new=AsyncMock(return_value=[]),
    ) as mocked:
        await tmdb_search.search_with_cache(db_session, "a")
        await tmdb_search.search_with_cache(db_session, "a")  # hit
    assert mocked.call_count == 1

    cleared = tmdb_search.clear_cache()
    assert cleared == 1

    stats = tmdb_search.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["keys"] == 0


@pytest.mark.asyncio
async def test_cache_keys_differentiate_pages_and_options(db_session):
    """Different page/language/available_only combos must not collide."""
    with patch(
        "services.portal.tmdb_search.search_tmdb_multi",
        new=AsyncMock(return_value=[]),
    ) as mocked:
        await tmdb_search.search_with_cache(db_session, "x", page=1)
        await tmdb_search.search_with_cache(db_session, "x", page=2)
        await tmdb_search.search_with_cache(
            db_session, "x", page=1, available_only=True
        )
        await tmdb_search.search_with_cache(
            db_session, "x", page=1, language="fr"
        )
    assert mocked.call_count == 4

    stats = tmdb_search.get_cache_stats()
    assert stats["keys"] == 4
    assert stats["misses"] == 4


@pytest.mark.asyncio
async def test_stats_payload_shape():
    """The admin panel relies on this exact key set."""
    stats = tmdb_search.get_cache_stats()
    assert set(stats.keys()) == {
        "name",
        "hits",
        "misses",
        "keys",
        "max_keys",
        "ttl_seconds",
        "value_bytes",
    }
    assert stats["name"] == "The Movie Database API"
    assert stats["ttl_seconds"] == 300
