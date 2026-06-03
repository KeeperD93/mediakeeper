"""get_media_detail: viewer-locale selection + English overview fallback.

The main-app detail used to hardcode the module LANGUAGE and ignore the
viewer. It now takes a 2-letter ``locale``, maps it to a TMDB code, and
falls back to the English overview when the localized one is empty.
"""
from unittest.mock import AsyncMock, patch

import pytest

import services.tmdb as tmdb_service


def _resp(payload, status=200):
    r = AsyncMock()
    r.status_code = status
    r.json = lambda: payload  # json() is called synchronously in the service
    return r


@pytest.fixture
def _key(monkeypatch):
    async def _fake_key(db=None):
        return "k"
    monkeypatch.setattr(tmdb_service, "_get_tmdb_key", _fake_key)


@pytest.mark.asyncio
async def test_media_detail_uses_viewer_locale(_key):
    client = AsyncMock()
    client.get = AsyncMock(return_value=_resp({
        "id": 1, "name": "EN Title", "overview": "EN overview",
        "first_air_date": "2020-05-01", "vote_average": 8.0,
    }))
    with patch("services.tmdb.get_external_client", return_value=client):
        out = await tmdb_service.get_media_detail("tv", 1, None, locale="en")
    assert out["title"] == "EN Title"
    assert out["overview"] == "EN overview"
    assert client.get.await_args.kwargs["params"]["language"] == "en-US"
    assert client.get.await_count == 1  # overview present -> no cascade


@pytest.mark.asyncio
async def test_media_detail_overview_cascades_to_english(_key):
    fr = _resp({"id": 1, "name": "FR Titre", "overview": "", "first_air_date": "2020-05-01"})
    en = _resp({"id": 1, "name": "EN Title", "overview": "English overview"})
    client = AsyncMock()
    client.get = AsyncMock(side_effect=[fr, en])
    with patch("services.tmdb.get_external_client", return_value=client):
        out = await tmdb_service.get_media_detail("tv", 1, None, locale="fr")
    # Title stays localized; only the empty overview falls back to English.
    assert out["title"] == "FR Titre"
    assert out["overview"] == "English overview"
    assert client.get.await_count == 2
    assert client.get.await_args_list[0].kwargs["params"]["language"] == "fr-FR"
    assert client.get.await_args_list[1].kwargs["params"]["language"] == "en-US"


@pytest.mark.asyncio
async def test_media_detail_no_cascade_when_overview_present(_key):
    client = AsyncMock()
    client.get = AsyncMock(return_value=_resp({
        "id": 1, "name": "FR Titre", "overview": "Résumé en français",
        "first_air_date": "2020-05-01",
    }))
    with patch("services.tmdb.get_external_client", return_value=client):
        out = await tmdb_service.get_media_detail("tv", 1, None, locale="fr")
    assert out["overview"] == "Résumé en français"
    assert client.get.await_count == 1
