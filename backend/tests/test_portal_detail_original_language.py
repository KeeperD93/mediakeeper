"""Detail payload exposes ISO codes so the frontend can localise labels (bug #95).

TMDB does not consistently translate language and country names, so the
backend now ships ``original_language`` (ISO 639-1) and ``country_codes``
(ISO 3166-1 alpha-2). The portal formats them client-side through
``Intl.DisplayNames`` according to the active i18n locale.
"""
from __future__ import annotations

import pytest

from services.portal import discover_details
from services.portal.discover_details import _details


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def get(self, _url, *, params, headers):
        return _FakeResponse(self._payload)


async def _fake_tmdb_key(_db):
    return "test-key"


def _movie_payload(*, original_language="fr", production_countries=None):
    return {
        "id": 4242,
        "title": "Les rayons et les ombres",
        "original_title": "Les rayons et les ombres",
        "overview": "Synopsis.",
        "release_date": "2024-01-01",
        "vote_average": 7.0,
        "popularity": 1.0,
        "original_language": original_language,
        "spoken_languages": [],
        "production_countries": (
            production_countries if production_countries is not None else [{"iso_3166_1": "FR"}]
        ),
        "genres": [],
        "credits": {"cast": [], "crew": []},
        "videos": {"results": []},
        "recommendations": {"results": []},
        "keywords": {"keywords": []},
        "reviews": {"results": []},
        "production_companies": [],
        "release_dates": {"results": []},
    }


@pytest.mark.asyncio
async def test_detail_payload_exposes_iso_codes(monkeypatch, db_session):
    payload = _movie_payload(
        original_language="en",
        production_countries=[{"iso_3166_1": "US"}, {"iso_3166_1": "GB"}],
    )
    monkeypatch.setattr(_details, "get_external_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(_details, "_get_tmdb_key", _fake_tmdb_key)

    async def _no_merge(*_args, **_kwargs):
        return None

    monkeypatch.setattr(_details, "merge_original_language_videos", _no_merge)

    result = await discover_details.get_full_details(db_session, "movie", 4242)

    assert result is not None
    assert result["original_language"] == "en"
    assert result["country_codes"] == ["US", "GB"]
    # The detail payload must no longer ship the localised label fields:
    # the frontend resolves them client-side via Intl.DisplayNames.
    assert "original_language_label" not in result
    assert "countries" not in result


@pytest.mark.asyncio
async def test_detail_payload_uppercases_iso_codes(monkeypatch, db_session):
    payload = _movie_payload(
        original_language="fr",
        production_countries=[{"iso_3166_1": "fr"}],
    )
    monkeypatch.setattr(_details, "get_external_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(_details, "_get_tmdb_key", _fake_tmdb_key)

    async def _no_merge(*_args, **_kwargs):
        return None

    monkeypatch.setattr(_details, "merge_original_language_videos", _no_merge)

    result = await discover_details.get_full_details(db_session, "movie", 4242)

    assert result is not None
    assert result["country_codes"] == ["FR"]


@pytest.mark.asyncio
async def test_detail_payload_handles_missing_countries(monkeypatch, db_session):
    payload = _movie_payload(
        original_language="ja",
        production_countries=[],
    )
    monkeypatch.setattr(_details, "get_external_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(_details, "_get_tmdb_key", _fake_tmdb_key)

    async def _no_merge(*_args, **_kwargs):
        return None

    monkeypatch.setattr(_details, "merge_original_language_videos", _no_merge)

    result = await discover_details.get_full_details(db_session, "movie", 4242)

    assert result is not None
    assert result["original_language"] == "ja"
    assert result["country_codes"] == []
