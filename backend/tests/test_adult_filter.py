"""Adult-content filtering for TMDB catalog responses (#289 Phase 1)."""
from services.portal.adult_filter import drop_adult
from services.portal.discover_lists import _normalize


def test_drop_adult_removes_flagged_when_hiding():
    items = [{"tmdb_id": 1, "adult": False}, {"tmdb_id": 2, "adult": True}]
    assert drop_adult(items, hide_adult=True) == [{"tmdb_id": 1, "adult": False}]


def test_drop_adult_keeps_everything_when_not_hiding():
    items = [{"tmdb_id": 1, "adult": False}, {"tmdb_id": 2, "adult": True}]
    assert drop_adult(items, hide_adult=True) != items
    assert drop_adult(items, hide_adult=False) == items


def test_drop_adult_handles_empty_and_none():
    assert drop_adult([], hide_adult=True) == []
    assert drop_adult(None, hide_adult=True) == []


def test_normalize_carries_adult_flag():
    assert _normalize({"id": 5, "title": "X", "adult": True})["adult"] is True
    # Absent flag normalises to False so existing TMDB rows stay visible.
    assert _normalize({"id": 6, "title": "Y"})["adult"] is False
