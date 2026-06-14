"""_search_tmdb backfills a blank localized overview from the English
search results with a single extra call (same cascade as
get_season_episodes / get_media_detail), and never makes that call when
it is not needed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import services.tmdb as tmdb_service


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _fake_client_by_language(by_lang: dict[str, dict], calls: list):
    """Client whose ``.get`` answers from ``by_lang`` keyed on the requested
    ``language`` param, recording each language queried in ``calls``."""
    fake_client = AsyncMock()

    async def get(url, *, params, headers, **kwargs):
        calls.append(params.get("language"))
        return _FakeResponse(by_lang.get(params.get("language"), {"results": []}))

    fake_client.get = get
    return fake_client


@pytest.fixture(autouse=True)
def _set_tmdb_key(monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    tmdb_service.invalidate_tmdb_key_cache()
    yield
    tmdb_service.invalidate_tmdb_key_cache()


@pytest.mark.asyncio
async def test_blank_localized_overview_falls_back_to_english():
    calls: list = []
    by_lang = {
        "fr-FR": {"results": [{"id": 7, "title": "Film", "overview": "  "}]},
        "en-US": {"results": [{"id": 7, "title": "Film", "overview": "An English synopsis."}]},
    }
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_by_language(by_lang, calls),
    ):
        out = await tmdb_service._search_tmdb("movie", "foo", language="fr-FR")

    assert out[0]["overview"] == "An English synopsis."
    assert "en-US" in calls  # the fallback call was issued


@pytest.mark.asyncio
async def test_present_localized_overview_skips_english_call():
    calls: list = []
    by_lang = {
        "fr-FR": {"results": [{"id": 7, "title": "Film", "overview": "Synopsis FR."}]},
    }
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_by_language(by_lang, calls),
    ):
        out = await tmdb_service._search_tmdb("movie", "foo", language="fr-FR")

    assert out[0]["overview"] == "Synopsis FR."
    assert calls == ["fr-FR"]  # no fallback call when nothing is blank


@pytest.mark.asyncio
async def test_english_locale_never_makes_fallback_call():
    calls: list = []
    by_lang = {
        "en-US": {"results": [{"id": 7, "title": "Film", "overview": ""}]},
    }
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_by_language(by_lang, calls),
    ):
        out = await tmdb_service._search_tmdb("tv", "foo", language="en-US")

    assert out[0]["overview"] == ""  # nothing to fall back to
    assert calls == ["en-US"]  # no second call even though the overview is blank
