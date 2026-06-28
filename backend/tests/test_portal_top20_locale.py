"""The Top 20 of the month is a single shared (global) ranking, but its item
titles are re-resolved to each viewer's locale at read time — the cached base
payload never leaks one viewer's language to another (#288)."""
from __future__ import annotations

import pytest

from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


async def _auth(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="top20-i18n", display_name="V", role="viewer",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))


@pytest.mark.asyncio
async def test_top20_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}

    async def _localize(db, items, locale):
        captured["locale"] = locale
        return items

    monkeypatch.setattr("api.portal.top20.localize_emby_items", _localize)
    r = await client.get("/api/portal/top20", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["locale"] == "en"


@pytest.mark.asyncio
async def test_top20_localizes_each_viewer_independently(client, db_session, monkeypatch):
    """Two viewers hit the same (cached) base ranking but each gets their own
    locale applied — proves the shared base cache does not leak languages."""
    await _auth(client, db_session)
    seen = []

    async def _localize(db, items, locale):
        seen.append(locale)
        return items

    monkeypatch.setattr("api.portal.top20.localize_emby_items", _localize)
    r1 = await client.get("/api/portal/top20", headers={"X-MK-Locale": "en"})
    r2 = await client.get("/api/portal/top20", headers={"X-MK-Locale": "fr"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert seen == ["en", "fr"]
