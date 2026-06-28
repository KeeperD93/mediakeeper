"""Trailer endpoints follow the viewer's active locale (X-MK-Locale), not the
stored profile language: the random carousel localizes its item titles and
both endpoints query the trailer cascade in the viewer's language (#288)."""
from __future__ import annotations

import pytest

from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


async def _auth(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="trailer-i18n", display_name="V", role="viewer",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))


@pytest.mark.asyncio
async def test_resolve_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, media_type, tmdb_id, user_language="en", emby_item_id=None):
        captured["lang"] = user_language
        return []

    monkeypatch.setattr("api.portal.trailers.resolve_trailers", _fake)
    r = await client.get(
        "/api/portal/trailers/resolve?media_type=movie&tmdb_id=603",
        headers={"X-MK-Locale": "en"},
    )
    assert r.status_code == 200, r.text
    assert captured["lang"] == "en"


@pytest.mark.asyncio
async def test_resolve_defaults_without_header(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _fake(db, media_type, tmdb_id, user_language="en", emby_item_id=None):
        captured["lang"] = user_language
        return []

    monkeypatch.setattr("api.portal.trailers.resolve_trailers", _fake)
    r = await client.get("/api/portal/trailers/resolve?media_type=movie&tmdb_id=603")
    assert r.status_code == 200, r.text
    assert captured["lang"] == "fr"  # no header -> instance default locale


@pytest.mark.asyncio
async def test_random_localizes_titles_and_cascade(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _recent(db, limit):
        return [{"tmdb_id": 1, "media_type": "movie", "title": "X", "emby_item_id": None}]

    async def _localize(db, items, locale):
        captured["loc_locale"] = locale
        return items

    async def _resolve(db, media_type, tmdb_id, user_language="en", emby_item_id=None):
        captured["cascade_lang"] = user_language
        return {"key": "abc", "source": "youtube"}

    monkeypatch.setattr("services.portal.available.get_recently_added", _recent)
    monkeypatch.setattr("api.portal.trailers.localize_emby_items", _localize)
    monkeypatch.setattr("api.portal.trailers.resolve_trailer", _resolve)
    r = await client.get("/api/portal/trailers/random?limit=5", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["loc_locale"] == "en"   # titles re-resolved in the viewer locale
    assert captured["cascade_lang"] == "en"  # trailer cascade in the viewer locale
