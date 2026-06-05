"""Adult-content filtering for TMDB catalog responses."""
import pytest

from services.portal.adult_filter import (
    ADULT_KEYWORD_IDS,
    ADULT_KEYWORDS_CSV,
    drop_adult,
    has_adult_keyword,
)
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


def test_adult_keyword_set_is_precise():
    assert 198385 in ADULT_KEYWORD_IDS  # hentai
    assert 155477 in ADULT_KEYWORD_IDS  # softcore
    # Borderline-but-legit markers stay OUT to avoid hiding mainstream titles.
    assert 256466 not in ADULT_KEYWORD_IDS  # erotic (erotic thrillers)
    assert 195669 not in ADULT_KEYWORD_IDS  # ecchi (fan-service anime)
    assert 161919 not in ADULT_KEYWORD_IDS  # adult animation (South Park…)
    assert ADULT_KEYWORDS_CSV == ",".join(str(k) for k in ADULT_KEYWORD_IDS)


def test_has_adult_keyword_detects_adult_ids():
    assert has_adult_keyword({198385}) is True          # hentai
    assert has_adult_keyword([155477, 18]) is True       # softcore + drama
    assert has_adult_keyword({18, 28}) is False          # drama + action only
    assert has_adult_keyword([]) is False
    assert has_adult_keyword(None) is False


@pytest.mark.asyncio
async def test_create_request_blocks_adult_when_disabled(db_session, monkeypatch):
    """A non-admin cannot request adult content while the admin policy is off."""
    from services.portal import requests_create

    async def _flag(db, key):
        return False

    async def _keywords(media_type, tmdb_id, db=None):
        return {198385}  # hentai

    monkeypatch.setattr("services.portal.admin.get_portal_flag", _flag)
    monkeypatch.setattr("services.tmdb.get_keyword_ids", _keywords)

    result = await requests_create.create_request(
        db_session, 1,
        {"tmdb_id": 999999, "media_type": "movie", "title": "X"},
        is_admin=False,
    )
    assert result == {"error": "adult_requests_disabled"}
