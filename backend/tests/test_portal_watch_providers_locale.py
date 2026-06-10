"""watch-providers endpoint requests TMDB in the viewer's active locale
(X-MK-Locale header) instead of a hardcoded fr-FR."""
from __future__ import annotations

import pytest

from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


class _FakeResponse:
    status_code = 200

    @staticmethod
    def json():
        return {"results": []}


def _fake_client(captured):
    class _Client:
        async def get(self, url, params=None, headers=None):
            captured["language"] = (params or {}).get("language")
            return _FakeResponse()

    return _Client()


async def _fake_key(db):
    return "test-key"


async def _auth(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="wp-i18n", display_name="V", role="viewer",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))


def _stub_tmdb(monkeypatch, captured):
    monkeypatch.setattr("services.tmdb._get_tmdb_key", _fake_key)
    monkeypatch.setattr("core.http_client.get_external_client", lambda: _fake_client(captured))


@pytest.mark.asyncio
async def test_watch_providers_uses_request_locale(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}
    _stub_tmdb(monkeypatch, captured)
    r = await client.get(
        "/api/portal/catalog/watch-providers", headers={"X-MK-Locale": "en"},
    )
    assert r.status_code == 200, r.text
    assert captured["language"] == "en-US"


@pytest.mark.asyncio
async def test_watch_providers_defaults_without_header(client, db_session, monkeypatch):
    await _auth(client, db_session)
    captured = {}
    _stub_tmdb(monkeypatch, captured)
    r = await client.get("/api/portal/catalog/watch-providers")  # no header -> default locale
    assert r.status_code == 200, r.text
    assert captured["language"] == "fr-FR"
