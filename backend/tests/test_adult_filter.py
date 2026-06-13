"""Adult-content filtering for TMDB catalog responses."""
from types import SimpleNamespace

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


def test_allow_adult_requests_flag_registered_and_off_by_default():
    from services.portal.admin import PORTAL_SETTING_FLAGS
    assert PORTAL_SETTING_FLAGS.get("portal.allow_adult_requests") is False


def test_patch_schema_accepts_allow_adult_requests():
    from api.portal.admin import PortalSettingsUpdate
    assert PortalSettingsUpdate(allow_adult_requests=True).allow_adult_requests is True


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

    async def _keywords(media_type, tmdb_id, db=None, *, strict=False):
        return {198385}  # hentai

    monkeypatch.setattr("services.portal.admin.get_portal_flag", _flag)
    monkeypatch.setattr("services.tmdb.get_keyword_ids", _keywords)

    result = await requests_create.create_request(
        db_session, 1,
        {"tmdb_id": 999999, "media_type": "movie", "title": "X"},
        is_admin=False,
    )
    assert result == {"error": "adult_requests_disabled"}


class _BoomClient:
    """TMDB client stub whose every request raises — simulates an outage."""

    async def get(self, *args, **kwargs):
        raise RuntimeError("tmdb down")


class _StatusClient:
    """TMDB client stub returning a non-200 response — a TMDB-side error
    (rate limit, 5xx) that arrives as a real Response, not a transport
    exception, so it exercises the status_code branch of get_keyword_ids."""

    def __init__(self, status_code):
        self._status_code = status_code

    async def get(self, *args, **kwargs):
        return SimpleNamespace(status_code=self._status_code, json=lambda: {})


@pytest.mark.asyncio
async def test_get_keyword_ids_strict_raises_on_tmdb_error(monkeypatch):
    from services import tmdb

    async def _key(db=None):
        return "tmdb-key"

    monkeypatch.setattr("services.tmdb._get_tmdb_key", _key)
    monkeypatch.setattr("services.tmdb.get_external_client", lambda: _BoomClient())
    with pytest.raises(tmdb.TmdbUnavailable):
        await tmdb.get_keyword_ids("movie", 1, None, strict=True)


@pytest.mark.asyncio
async def test_get_keyword_ids_lenient_swallows_tmdb_error(monkeypatch):
    from services import tmdb

    async def _key(db=None):
        return "tmdb-key"

    monkeypatch.setattr("services.tmdb._get_tmdb_key", _key)
    monkeypatch.setattr("services.tmdb.get_external_client", lambda: _BoomClient())
    assert await tmdb.get_keyword_ids("movie", 1, None) == set()


@pytest.mark.asyncio
async def test_get_keyword_ids_strict_raises_on_non_200(monkeypatch):
    # A non-200 TMDB response (503 here) is a genuine error distinct from a
    # transport failure: strict mode must raise so the adult-request guard
    # fails closed rather than treat an unverifiable item as clean.
    from services import tmdb

    async def _key(db=None):
        return "tmdb-key"

    monkeypatch.setattr("services.tmdb._get_tmdb_key", _key)
    monkeypatch.setattr("services.tmdb.get_external_client", lambda: _StatusClient(503))
    with pytest.raises(tmdb.TmdbUnavailable):
        await tmdb.get_keyword_ids("movie", 1, None, strict=True)


@pytest.mark.asyncio
async def test_get_keyword_ids_lenient_swallows_non_200(monkeypatch):
    from services import tmdb

    async def _key(db=None):
        return "tmdb-key"

    monkeypatch.setattr("services.tmdb._get_tmdb_key", _key)
    monkeypatch.setattr("services.tmdb.get_external_client", lambda: _StatusClient(503))
    assert await tmdb.get_keyword_ids("movie", 1, None) == set()


@pytest.mark.asyncio
async def test_get_keyword_ids_no_key_never_blocks(monkeypatch):
    # No TMDB key is a permanent config state, not an outage: the check is
    # inoperative and must never block, even in strict mode.
    from services import tmdb

    async def _no_key(db=None):
        return ""

    monkeypatch.setattr("services.tmdb._get_tmdb_key", _no_key)
    assert await tmdb.get_keyword_ids("movie", 1, None, strict=True) == set()


@pytest.mark.asyncio
async def test_create_request_fails_closed_when_adult_check_unavailable(db_session, monkeypatch):
    """A TMDB outage blocks the request instead of silently allowing it while
    the adult-requests policy is off."""
    from services.portal import requests_create
    from services.tmdb import TmdbUnavailable

    async def _flag(db, key):
        return False

    async def _keywords(media_type, tmdb_id, db=None, *, strict=False):
        raise TmdbUnavailable("tmdb_down")

    monkeypatch.setattr("services.portal.admin.get_portal_flag", _flag)
    monkeypatch.setattr("services.tmdb.get_keyword_ids", _keywords)

    result = await requests_create.create_request(
        db_session, 1,
        {"tmdb_id": 999999, "media_type": "movie", "title": "X"},
        is_admin=False,
    )
    assert result == {"error": "adult_check_unavailable"}
