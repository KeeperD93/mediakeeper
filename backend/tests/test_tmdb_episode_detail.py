"""Localized TMDB season/episode detail helpers: region-expand the locale and
cascade to English on a blank overview (#288 Discord notifications)."""
from __future__ import annotations

import pytest

from services import tmdb_episode


class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _Client:
    """Returns the given payloads in call order; records each ``language``."""

    def __init__(self, payloads):
        self._payloads = payloads
        self.langs: list[str | None] = []

    async def get(self, _url, *, params=None, headers=None):
        idx = min(len(self.langs), len(self._payloads) - 1)
        self.langs.append((params or {}).get("language"))
        return _Resp(self._payloads[idx])


async def _fake_key(_db=None):
    return "test-key"


def _wire(monkeypatch, payloads):
    client = _Client(payloads)
    monkeypatch.setattr(tmdb_episode, "get_external_client", lambda: client)
    monkeypatch.setattr(tmdb_episode, "_get_tmdb_key", _fake_key)
    return client


@pytest.mark.asyncio
async def test_episode_detail_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, [{"name": "Ozymandias", "overview": "Synopsis"}])
    out = await tmdb_episode.get_episode_detail(1396, 5, 14, db_session, locale="en")
    assert client.langs == ["en-US"]
    assert out == {"name": "Ozymandias", "overview": "Synopsis"}


@pytest.mark.asyncio
async def test_episode_detail_cascades_en_on_blank_overview(monkeypatch, db_session):
    client = _wire(monkeypatch, [
        {"name": "Titre", "overview": ""},
        {"name": "Title", "overview": "EN synopsis"},
    ])
    out = await tmdb_episode.get_episode_detail(1396, 5, 14, db_session, locale="de")
    assert client.langs == ["de-DE", "en-US"]  # region-expanded, then EN cascade
    assert out["overview"] == "EN synopsis"
    assert out["name"] == "Titre"  # name stays from the requested locale call


@pytest.mark.asyncio
async def test_season_detail_expands_region(monkeypatch, db_session):
    client = _wire(monkeypatch, [{"name": "Saison 1", "overview": "o"}])
    out = await tmdb_episode.get_season_detail(1396, 1, db_session, locale="en")
    assert client.langs == ["en-US"]
    assert out["name"] == "Saison 1"


@pytest.mark.asyncio
async def test_detail_empty_without_key(monkeypatch, db_session):
    async def _no_key(_db=None):
        return ""

    monkeypatch.setattr(tmdb_episode, "_get_tmdb_key", _no_key)
    out = await tmdb_episode.get_season_detail(1396, 1, db_session, locale="en")
    assert out == {}
