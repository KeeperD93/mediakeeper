"""Catalog/discover siblings expand the 2-letter viewer locale to a TMDB
``xx-YY`` region code via ``tmdb_language()`` — the same canonical helper
``get_full_details`` already uses — instead of passing the raw 2-letter code.

Companion to ``test_portal_discover_locale`` (which checks the right locale
reaches the service) — these go one layer deeper and assert the exact
``language`` value sent to TMDB (#288).
"""
from __future__ import annotations

import pytest

from services import tmdb
from services.portal import discover_lists
from services.portal.discover_details import _details


class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _CapturingClient:
    """Records the ``language`` query param of every TMDB call."""

    def __init__(self, payload):
        self._payload = payload
        self.langs: list[str | None] = []

    async def get(self, _url, *, params=None, headers=None):
        self.langs.append((params or {}).get("language"))
        return _Resp(self._payload)


async def _fake_key(_db=None):
    return "test-key"


def _wire(monkeypatch, module, payload):
    client = _CapturingClient(payload)
    monkeypatch.setattr(module, "get_external_client", lambda: client)
    monkeypatch.setattr(module, "_get_tmdb_key", _fake_key)
    return client


@pytest.mark.asyncio
async def test_person_filmography_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, _details, {"id": 1, "name": "X", "cast": [], "crew": []})
    await _details.get_person_filmography(db_session, 1, language="en")
    assert client.langs == ["en-US", "en-US"]


@pytest.mark.asyncio
async def test_collection_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, _details, {"id": 1, "name": "C", "parts": []})
    await _details.get_collection(db_session, 10, language="en")
    assert client.langs == ["en-US"]


@pytest.mark.asyncio
async def test_media_videos_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, discover_lists, {"results": []})
    await discover_lists.get_media_videos(db_session, "movie", 603, language="en")
    assert client.langs == ["en-US"]


@pytest.mark.asyncio
async def test_discover_list_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, discover_lists, {"results": []})
    await discover_lists._fetch_list_params(db_session, "/discover/movie", 1, {}, language="en")
    assert client.langs == ["en-US"]


@pytest.mark.asyncio
async def test_tv_seasons_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, tmdb, {"seasons": []})
    await tmdb.get_tv_seasons(123, db_session, language="en")
    assert client.langs == ["en-US"]


@pytest.mark.asyncio
async def test_season_episodes_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, tmdb, {"episodes": []})
    await tmdb.get_season_episodes(123, 1, db_session, language="en")
    assert client.langs == ["en-US"]


@pytest.mark.asyncio
async def test_region_expansion_maps_pt_to_br(monkeypatch, db_session):
    """The win for region-aware locales: pt -> pt-BR, not a bare pt."""
    client = _wire(monkeypatch, discover_lists, {"results": []})
    await discover_lists._fetch_list_params(db_session, "/discover/movie", 1, {}, language="pt")
    assert client.langs == ["pt-BR"]


@pytest.mark.asyncio
async def test_default_locale_stays_portal_language(monkeypatch, db_session):
    """No regression for the default: language=None -> fr-FR (unchanged)."""
    client = _wire(monkeypatch, discover_lists, {"results": []})
    await discover_lists._fetch_list_params(db_session, "/discover/movie", 1, {}, language=None)
    assert client.langs == ["fr-FR"]
