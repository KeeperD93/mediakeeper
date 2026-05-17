"""Original-language label resolution on the portal detail payload (bug #95).

TMDB exposes ``original_language`` as an ISO 639-1 code (``"fr"``), while
``spoken_languages`` is an arbitrarily ordered list whose entries carry a
localised ``name`` and an ``english_name``. The portal detail page must
display the label that matches ``original_language`` — not the first
spoken language, which could be a secondary track (e.g. German dialogue
in an otherwise French production).
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


def _movie_payload(*, original_language, spoken_languages, production_countries=None):
    return {
        "id": 4242,
        "title": "Les rayons et les ombres",
        "original_title": "Les rayons et les ombres",
        "overview": "Synopsis.",
        "release_date": "2024-01-01",
        "vote_average": 7.0,
        "popularity": 1.0,
        "original_language": original_language,
        "spoken_languages": spoken_languages,
        "production_countries": production_countries or [{"name": "France"}],
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
async def test_original_language_label_uses_matching_spoken_language(
    monkeypatch, db_session,
):
    payload = _movie_payload(
        original_language="fr",
        spoken_languages=[
            {"iso_639_1": "de", "name": "Allemand", "english_name": "German"},
            {"iso_639_1": "fr", "name": "Français", "english_name": "French"},
        ],
    )
    monkeypatch.setattr(_details, "get_external_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(_details, "_get_tmdb_key", _fake_tmdb_key)

    async def _no_merge(*_args, **_kwargs):
        return None

    monkeypatch.setattr(_details, "merge_original_language_videos", _no_merge)

    result = await discover_details.get_full_details(db_session, "movie", 4242)

    assert result is not None
    assert result["original_language"] == "fr"
    assert result["original_language_label"] == "Français"
    assert result["countries"] == ["France"]
    assert "languages" not in result


@pytest.mark.asyncio
async def test_original_language_label_falls_back_to_upper_code(
    monkeypatch, db_session,
):
    payload = _movie_payload(
        original_language="ja",
        spoken_languages=[
            {"iso_639_1": "en", "name": "Anglais", "english_name": "English"},
        ],
    )
    monkeypatch.setattr(_details, "get_external_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(_details, "_get_tmdb_key", _fake_tmdb_key)

    async def _no_merge(*_args, **_kwargs):
        return None

    monkeypatch.setattr(_details, "merge_original_language_videos", _no_merge)

    result = await discover_details.get_full_details(db_session, "movie", 4242)

    assert result is not None
    assert result["original_language"] == "ja"
    assert result["original_language_label"] == "JA"


@pytest.mark.asyncio
async def test_original_language_label_is_empty_when_code_missing(
    monkeypatch, db_session,
):
    payload = _movie_payload(
        original_language="",
        spoken_languages=[],
    )
    monkeypatch.setattr(_details, "get_external_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(_details, "_get_tmdb_key", _fake_tmdb_key)

    async def _no_merge(*_args, **_kwargs):
        return None

    monkeypatch.setattr(_details, "merge_original_language_videos", _no_merge)

    result = await discover_details.get_full_details(db_session, "movie", 4242)

    assert result is not None
    assert result["original_language"] == ""
    assert result["original_language_label"] == ""
