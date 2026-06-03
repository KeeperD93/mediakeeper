"""Filter / sort / cap + per-locale localization contract for
GET /api/watchlist/upcoming.

The endpoint reads the language-neutral upcoming structure from the
in-memory scanner cache, then re-resolves the series name / poster /
episode title in the viewer's language via the per-(id, lang) TMDB cache.
Both layers are injected via ``monkeypatch`` so the test needs neither a
real scan nor a real TMDB key.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

_UPCOMING = "/api/watchlist/upcoming"


def _iso(delta_days: int) -> str:
    """An ISO date ``delta_days`` away from today (negative = past)."""
    return (date.today() + timedelta(days=delta_days)).isoformat()


async def _fake_series(db, tmdb_id, lang):
    return {"name": f"Show{tmdb_id} [{lang}]", "poster_path": f"/p{tmdb_id}.jpg"}


async def _fake_season(db, tmdb_id, sn, lang):
    return {"episodes": [{"episode_number": e, "name": f"S{sn}E{e} [{lang}]"} for e in range(40)]}


def _patch_tmdb(monkeypatch):
    """Stub the per-language TMDB resolution the endpoint imports lazily."""
    monkeypatch.setattr("services.watchlist_scanner._tmdb._tmdb_series", _fake_series)
    monkeypatch.setattr("services.watchlist_scanner._tmdb._tmdb_season", _fake_season)


@pytest.mark.asyncio
async def test_upcoming_empty_when_scan_not_ready(authed_client, monkeypatch):
    monkeypatch.setattr("services.watchlist_scanner.get_scan_status", lambda: {"ready": False})
    r = await authed_client.get(_UPCOMING)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_upcoming_empty_when_cache_blank(authed_client, monkeypatch):
    monkeypatch.setattr("services.watchlist_scanner.get_scan_status", lambda: {"ready": True})
    monkeypatch.setattr("services.watchlist_scanner._cache", {})
    r = await authed_client.get(_UPCOMING)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_upcoming_filters_sorts_and_localizes(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    monkeypatch.setattr("services.watchlist_scanner.get_scan_status", lambda: {"ready": True})
    monkeypatch.setattr("services.watchlist_scanner._cache", {"series": [
        {"name": "Emby A", "tmdb_id": 7, "emby_poster": "/api/emby/image/x", "seasons": [
            {"season": 2, "episodes": [
                {"status": "upcoming", "air_date": _iso(10), "episode": 5},
                {"status": "upcoming", "air_date": _iso(-1), "episode": 4},
                {"status": "upcoming", "air_date": _iso(-5), "episode": 3},
                {"status": "aired", "air_date": _iso(3), "episode": 6},
                {"status": "upcoming", "air_date": "", "episode": 7},
            ]},
        ]},
    ]})
    r = await authed_client.get(_UPCOMING, params={"lang": "fr"})
    assert r.status_code == 200
    body = r.json()
    # Only the two in-window upcoming episodes survive, sorted asc, and the
    # display fields come from TMDB in the requested locale (fr -> fr-FR).
    assert [e["episode"] for e in body] == [4, 5]
    assert body[0] == {
        "series_name": "Show7 [fr-FR]",
        "poster": "https://image.tmdb.org/t/p/w300/p7.jpg",
        "tmdb_id": 7,
        "season": 2,
        "episode": 4,
        "episode_name": "S2E4 [fr-FR]",
        "air_date": _iso(-1),
    }


@pytest.mark.asyncio
async def test_upcoming_localizes_to_viewer_language(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    monkeypatch.setattr("services.watchlist_scanner.get_scan_status", lambda: {"ready": True})
    monkeypatch.setattr("services.watchlist_scanner._cache", {"series": [
        {"tmdb_id": 7, "emby_poster": "", "seasons": [
            {"season": 1, "episodes": [{"status": "upcoming", "air_date": _iso(2), "episode": 1}]},
        ]},
    ]})
    r = await authed_client.get(_UPCOMING, params={"lang": "en"})
    assert r.status_code == 200
    body = r.json()
    # English viewer -> TMDB en-US for every display field.
    assert body[0]["series_name"] == "Show7 [en-US]"
    assert body[0]["episode_name"] == "S1E1 [en-US]"


@pytest.mark.asyncio
async def test_upcoming_caps_at_30_keeping_earliest(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    episodes = [
        {"status": "upcoming", "air_date": _iso(i + 1), "episode": i}
        for i in range(35)
    ]
    monkeypatch.setattr("services.watchlist_scanner.get_scan_status", lambda: {"ready": True})
    monkeypatch.setattr("services.watchlist_scanner._cache", {"series": [
        {"tmdb_id": 1, "emby_poster": "", "seasons": [{"season": 1, "episodes": episodes}]},
    ]})
    r = await authed_client.get(_UPCOMING)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 30
    # The 30 earliest are kept (sorted asc, then [:30]).
    assert body[0]["air_date"] == _iso(1)
    assert body[-1]["air_date"] == _iso(30)
