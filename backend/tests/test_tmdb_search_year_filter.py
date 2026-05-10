"""TMDB search service forwards the optional ``year`` filter to the right
TMDB query parameter (``primary_release_year`` for movies,
``first_air_date_year`` for series), and never sends an empty/zero value.
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


def _fake_client_capturing(captured: dict):
    fake_client = AsyncMock()

    async def get(url, *, params, headers, **kwargs):
        captured["url"] = url
        captured["params"] = dict(params)
        captured["headers"] = dict(headers)
        return _FakeResponse({"results": []})

    fake_client.get = get
    return fake_client


@pytest.fixture(autouse=True)
def _set_tmdb_key(monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    tmdb_service.invalidate_tmdb_key_cache()
    yield
    tmdb_service.invalidate_tmdb_key_cache()


@pytest.mark.asyncio
async def test_search_movie_with_year_sends_primary_release_year():
    captured: dict = {}
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_capturing(captured),
    ):
        await tmdb_service._search_tmdb("movie", "foo", year=2023)

    assert captured["params"].get("primary_release_year") == 2023
    assert "first_air_date_year" not in captured["params"]


@pytest.mark.asyncio
async def test_search_tv_with_year_sends_first_air_date_year():
    captured: dict = {}
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_capturing(captured),
    ):
        await tmdb_service._search_tmdb("tv", "foo", year=2023)

    assert captured["params"].get("first_air_date_year") == 2023
    assert "primary_release_year" not in captured["params"]


@pytest.mark.asyncio
async def test_search_movie_without_year_omits_filter():
    captured: dict = {}
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_capturing(captured),
    ):
        await tmdb_service._search_tmdb("movie", "foo")

    assert "primary_release_year" not in captured["params"]
    assert "first_air_date_year" not in captured["params"]


@pytest.mark.asyncio
async def test_search_movie_year_none_omits_filter():
    captured: dict = {}
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_capturing(captured),
    ):
        await tmdb_service._search_tmdb("movie", "foo", year=None)

    assert "primary_release_year" not in captured["params"]
    assert "first_air_date_year" not in captured["params"]


@pytest.mark.asyncio
async def test_search_movie_year_zero_omits_filter():
    """A 0/empty value would make TMDB filter out every result — drop it."""
    captured: dict = {}
    with patch(
        "services.tmdb.get_external_client",
        return_value=_fake_client_capturing(captured),
    ):
        await tmdb_service._search_tmdb("movie", "foo", year=0)

    assert "primary_release_year" not in captured["params"]
