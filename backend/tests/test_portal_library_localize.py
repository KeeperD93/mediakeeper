"""Per-viewer localization of Emby-sourced portal library carousels.

Emby items carry Name/Overview in the library language. A viewer on a
non-default locale (via the ``X-MK-Locale`` header) gets title + synopsis
re-resolved through TMDB (stubbed here), cached per (id, media_type, lang),
while the default locale is served as-is and the input dicts are never mutated.
"""
from __future__ import annotations

import pytest

from services.portal import available_localize as al
from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token, make_portal_user


def _items() -> list[dict]:
    return [
        {"tmdb_id": 603, "media_type": "movie", "title": "Matrice", "overview": "fr o", "poster_url": "/p1"},
        {"tmdb_id": 1399, "media_type": "tv", "title": "Trone", "overview": "fr t", "poster_url": "/p2"},
        {"tmdb_id": None, "media_type": "movie", "title": "No TMDB", "overview": "keep", "poster_url": "/p3"},
    ]


async def _fake_key(db=None):
    return "test-key"


def _patch(monkeypatch, detail):
    al._meta_cache.clear()
    monkeypatch.setattr("services.portal.available_localize._get_tmdb_key", _fake_key)
    monkeypatch.setattr("services.portal.available_localize.get_media_detail", detail)


@pytest.mark.asyncio
async def test_default_locale_served_as_is(monkeypatch):
    called = []

    async def _detail(mt, tid, db=None, locale=None):
        called.append(tid)
        return {}

    _patch(monkeypatch, _detail)
    items = _items()
    out = await al.localize_emby_items(None, items, "fr")  # fr -> fr-FR (default), no re-resolution
    assert out is items
    assert called == []


@pytest.mark.asyncio
async def test_localizes_to_viewer_language(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]", "overview": f"O{tid} [{locale}]"}

    _patch(monkeypatch, _detail)
    out = await al.localize_emby_items(None, _items(), "en")
    assert out[0]["title"] == "T603 [en]"
    assert out[0]["overview"] == "O603 [en]"
    assert out[0]["poster_url"] == "/p1"  # non-localized fields preserved
    assert out[1]["title"] == "T1399 [en]"
    # Item without tmdb_id is left untouched.
    assert out[2]["title"] == "No TMDB"
    assert out[2]["overview"] == "keep"


@pytest.mark.asyncio
async def test_does_not_mutate_input(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "X", "overview": "Y"}

    _patch(monkeypatch, _detail)
    items = _items()
    await al.localize_emby_items(None, items, "en")
    assert items[0]["title"] == "Matrice"
    assert items[0]["overview"] == "fr o"


@pytest.mark.asyncio
async def test_blank_tmdb_values_fall_back_to_source(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "", "overview": ""}

    _patch(monkeypatch, _detail)
    out = await al.localize_emby_items(None, _items(), "en")
    assert out[0]["title"] == "Matrice"  # blank TMDB title -> keep Emby title
    assert out[0]["overview"] == "fr o"


@pytest.mark.asyncio
async def test_tmdb_error_keeps_source(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"error": "tmdb_detail_failed"}

    _patch(monkeypatch, _detail)
    out = await al.localize_emby_items(None, _items(), "en")
    assert out[0]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_no_tmdb_key_serves_as_is(monkeypatch):
    al._meta_cache.clear()
    called = []

    async def _no_key(db=None):
        return ""

    async def _detail(mt, tid, db=None, locale=None):
        called.append(tid)
        return {}

    monkeypatch.setattr("services.portal.available_localize._get_tmdb_key", _no_key)
    monkeypatch.setattr("services.portal.available_localize.get_media_detail", _detail)
    items = _items()
    out = await al.localize_emby_items(None, items, "en")
    assert out is items
    assert called == []


@pytest.mark.asyncio
async def test_cache_avoids_second_tmdb_call(monkeypatch):
    calls = []

    async def _detail(mt, tid, db=None, locale=None):
        calls.append(tid)
        return {"title": f"T{tid}", "overview": f"O{tid}"}

    _patch(monkeypatch, _detail)
    await al.localize_emby_items(None, _items(), "en")
    await al.localize_emby_items(None, _items(), "en")
    # 2 items carry a tmdb_id; each resolved once despite two passes.
    assert sorted(calls) == [603, 1399]


@pytest.mark.asyncio
async def test_recent_endpoint_localizes(client, db_session, monkeypatch):
    user, _ = await make_portal_user(
        db_session, username="i18n-recent", display_name="V", role="viewer",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    al._meta_cache.clear()

    async def _fake_recent(db, limit, enrich_rating=False):
        return [{"tmdb_id": 603, "media_type": "movie", "title": "Matrice", "overview": "fr"}]

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]", "overview": f"O{tid} [{locale}]"}

    monkeypatch.setattr("services.portal.available.get_recently_added", _fake_recent)
    monkeypatch.setattr("services.portal.available_localize._get_tmdb_key", _fake_key)
    monkeypatch.setattr("services.portal.available_localize.get_media_detail", _detail)

    r = await client.get("/api/portal/library/recent", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["title"] == "T603 [en]"
    assert item["overview"] == "O603 [en]"
