"""Discover/catalog lists follow the viewer's active locale (X-MK-Locale
header) instead of the stored profile language."""
from __future__ import annotations

import pytest

from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token, make_portal_user


async def _auth(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="disc-i18n", display_name="V", role="viewer",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))


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
