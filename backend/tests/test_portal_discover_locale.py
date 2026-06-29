"""Discover/catalog lists follow the viewer's active locale (X-MK-Locale
header) instead of the stored profile language."""
from __future__ import annotations

from collections import Counter

import pytest

from services.portal import media_title_localize as ml
from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token, make_portal_user


async def _auth(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="disc-i18n", display_name="V", role="viewer",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))


def _patch_localize(monkeypatch):
    """Make ``localize_titles`` actually re-resolve (non-default locale) via a
    stubbed TMDB, so the route's localization wiring is exercised end-to-end."""
    ml._title_cache.clear()

    async def _key(db=None):
        return "test-key"

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]"}

    monkeypatch.setattr("services.portal.media_title_localize._get_tmdb_key", _key)
    monkeypatch.setattr("services.portal.media_title_localize.get_media_detail", _detail)


@pytest.mark.asyncio
async def test_trending_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, page=1, *, language=None, include_adult=False):
        captured["language"] = language
        return []

    monkeypatch.setattr("services.portal.discover.get_trending", _fake)
    r = await client.get("/api/portal/catalog/trending", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["language"] == "en"


@pytest.mark.asyncio
async def test_trending_defaults_without_header(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, page=1, *, language=None, include_adult=False):
        captured["language"] = language
        return []

    monkeypatch.setattr("services.portal.discover.get_trending", _fake)
    r = await client.get("/api/portal/catalog/trending")  # no header -> default locale
    assert r.status_code == 200, r.text
    assert captured["language"] == "fr"


@pytest.mark.asyncio
async def test_category_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, category, page=1, sort="popularity", language=None, include_adult=False):
        captured["language"] = language
        return {"items": [], "page": page, "has_more": False}

    monkeypatch.setattr("services.portal.discover.discover_category", _fake)
    r = await client.get("/api/portal/catalog/category/movies", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["language"] == "en"


@pytest.mark.asyncio
async def test_watch_history_category_localizes_titles(client, db_session, monkeypatch):
    """The watch-history browse category re-resolves item titles per viewer."""
    await _auth(client, db_session)

    async def _fake(db, user, profile, page=1, **kw):
        return {
            "items": [{"tmdb_id": 603, "media_type": "movie", "title": "Matrice"}],
            "page": page, "has_more": False,
        }

    monkeypatch.setattr("services.portal.profile_stats.get_watch_history_paginated", _fake)
    _patch_localize(monkeypatch)

    r = await client.get(
        "/api/portal/catalog/category/watch-history", headers={"X-MK-Locale": "en"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["title"] == "T603 [en]"

    ml._title_cache.clear()
    r_fr = await client.get("/api/portal/catalog/category/watch-history")  # default -> as-is
    assert r_fr.json()["items"][0]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_my_requests_category_localizes_titles(client, db_session, monkeypatch):
    """The my-requests browse category re-resolves item titles per viewer."""
    await _auth(client, db_session)

    async def _fake(db, user, page=1, **kw):
        return {
            "items": [{"tmdb_id": 1399, "media_type": "tv", "title": "Trône"}],
            "page": page, "has_more": False,
        }

    monkeypatch.setattr("services.portal.profile_stats.get_my_requests_paginated", _fake)
    _patch_localize(monkeypatch)

    r = await client.get(
        "/api/portal/catalog/category/my-requests", headers={"X-MK-Locale": "en"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["title"] == "T1399 [en]"


@pytest.mark.asyncio
async def test_person_filmography_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, person_id, role="all", media_filter="all", *, language=None):
        captured["language"] = language
        return {"person": None, "items": []}

    monkeypatch.setattr("api.portal.catalog._detail.get_person_filmography", _fake)
    r = await client.get("/api/portal/catalog/person/123", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["language"] == "en"


@pytest.mark.asyncio
async def test_person_filmography_defaults_without_header(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, person_id, role="all", media_filter="all", *, language=None):
        captured["language"] = language
        return {"person": None, "items": []}

    monkeypatch.setattr("api.portal.catalog._detail.get_person_filmography", _fake)
    r = await client.get("/api/portal/catalog/person/123")  # no header -> default locale
    assert r.status_code == 200, r.text
    assert captured["language"] == "fr"


@pytest.mark.asyncio
async def test_collection_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, collection_id, *, language=None):
        captured["language"] = language
        return {"collection": None, "items": []}

    monkeypatch.setattr("api.portal.catalog._detail.get_collection", _fake)
    r = await client.get("/api/portal/catalog/collection/10", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["language"] == "en"


@pytest.mark.asyncio
async def test_videos_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, media_type, tmdb_id, *, language=None):
        captured["language"] = language
        return []

    monkeypatch.setattr("services.portal.discover.get_media_videos", _fake)
    r = await client.get("/api/portal/catalog/videos/movie/603", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["language"] == "en"


@pytest.mark.asyncio
async def test_media_detail_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, media_type, tmdb_id, *, language=None):
        captured["language"] = language
        return {"title": "X", "recommendations": []}

    monkeypatch.setattr("services.portal.discover.get_full_details", _fake)
    r = await client.get("/api/portal/catalog/detail/movie/603", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["language"] == "en"


@pytest.mark.asyncio
async def test_media_detail_defaults_without_header(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, media_type, tmdb_id, *, language=None):
        captured["language"] = language
        return {"title": "X", "recommendations": []}

    monkeypatch.setattr("services.portal.discover.get_full_details", _fake)
    r = await client.get("/api/portal/catalog/detail/movie/603")  # no header -> default locale
    assert r.status_code == 200, r.text
    assert captured["language"] == "fr"


@pytest.mark.asyncio
async def test_recommended_for_me_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _reco(db, user, profile, *, locale=None):
        captured["locale"] = locale
        return []

    monkeypatch.setattr("services.portal.personal.get_recommendations_for_user", _reco)
    r = await client.get("/api/portal/catalog/recommended-for-me", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["locale"] == "en"


@pytest.mark.asyncio
async def test_recommendations_full_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _reco(db, user, profile, *, locale=None):
        captured["locale"] = locale
        return []

    async def _zero(db, user, profile):
        return 0

    async def _infer(db, user, profile):
        return [], Counter()

    monkeypatch.setattr("services.portal.personal.get_recommendations_for_user", _reco)
    monkeypatch.setattr("services.portal.personal._count_total_plays", _zero)
    monkeypatch.setattr("services.portal.personal._infer_genres_from_history_full", _infer)
    r = await client.get("/api/portal/catalog/recommendations-full", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["locale"] == "en"


@pytest.mark.asyncio
async def test_recommended_full_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _reco(db, user, profile, *, locale=None):
        captured["locale"] = locale
        return []

    monkeypatch.setattr("services.portal.personal.get_recommendations_for_user", _reco)
    r = await client.get("/api/portal/catalog/recommended-full", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["locale"] == "en"


@pytest.mark.asyncio
async def test_preferences_based_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, profile, page=1, *, locale=None):
        captured["locale"] = locale
        return {"items": [], "page": page, "has_more": False}

    monkeypatch.setattr("services.portal.preferences_based.get_preferences_based", _fake)
    r = await client.get("/api/portal/catalog/preferences-based", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["locale"] == "en"
