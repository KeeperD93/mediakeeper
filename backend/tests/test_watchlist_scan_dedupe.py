"""Watchlist scan: deduplicate series sharing the same TMDB id.

Emby may expose the same TV series several times (split versions, multiple
libraries) and the resulting analyses then collide on `tmdb_id`, which is
the key the frontend uses to render the missing-series list. The scanner
must collapse them and keep the best Emby copy (lowest `missing_count`).
"""

from services.watchlist_scanner.scan import dedupe_by_tmdb


def _entry(tmdb_id: int, missing: int, name: str = "Series", series_id: str = "id"):
    return {
        "tmdb_id": tmdb_id,
        "missing_count": missing,
        "upcoming_count": 0,
        "name": name,
        "series_id": series_id,
    }


def test_dedupe_collapses_duplicate_tmdb_ids():
    series = [
        _entry(42, missing=5, name="Hell's Paradise", series_id="emby-A"),
        _entry(42, missing=5, name="Hell's Paradise", series_id="emby-B"),
        _entry(99, missing=2, name="Other"),
    ]

    result = dedupe_by_tmdb(series)

    tmdb_ids = sorted(r["tmdb_id"] for r in result)
    assert tmdb_ids == [42, 99]
    assert len([r for r in result if r["tmdb_id"] == 42]) == 1


def test_dedupe_keeps_copy_with_fewest_missing_episodes():
    series = [
        _entry(42, missing=12, series_id="incomplete"),
        _entry(42, missing=3, series_id="complete"),
        _entry(42, missing=8, series_id="middle"),
    ]

    result = dedupe_by_tmdb(series)

    assert len(result) == 1
    assert result[0]["series_id"] == "complete"
    assert result[0]["missing_count"] == 3


def test_dedupe_preserves_unique_series_unchanged():
    series = [
        _entry(1, missing=4),
        _entry(2, missing=0),
        _entry(3, missing=7),
    ]

    result = dedupe_by_tmdb(series)

    assert len(result) == 3
    assert sorted(r["tmdb_id"] for r in result) == [1, 2, 3]


def test_dedupe_passes_through_entries_without_tmdb_id():
    series = [
        {"tmdb_id": None, "missing_count": 1, "name": "Orphan A"},
        {"missing_count": 2, "name": "Orphan B"},
        _entry(7, missing=3),
    ]

    result = dedupe_by_tmdb(series)

    assert len(result) == 3
    names = sorted(r["name"] for r in result)
    assert names == ["Orphan A", "Orphan B", "Series"]


def test_dedupe_handles_empty_input():
    assert dedupe_by_tmdb([]) == []
