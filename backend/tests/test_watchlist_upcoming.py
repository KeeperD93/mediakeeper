"""Filter / sort / cap contract for GET /api/watchlist/upcoming.

The endpoint reads the in-memory scanner cache and returns upcoming episodes
whose ``air_date`` is within the last-2-days cutoff, sorted ascending and
capped at 30. None of that was pinned by a test, so a regression in the
cutoff, the status filter, the sort or the cap would pass CI unnoticed.

The scanner state is injected via ``monkeypatch`` on the module the route
imports lazily (``services.watchlist_scanner``), which auto-reverts and keeps
the test independent of any real scan.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

_UPCOMING = "/api/watchlist/upcoming"


def _iso(delta_days: int) -> str:
    """An ISO date ``delta_days`` away from today (negative = past)."""
    return (date.today() + timedelta(days=delta_days)).isoformat()


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
async def test_upcoming_filters_sorts_and_shapes(authed_client, monkeypatch):
    monkeypatch.setattr("services.watchlist_scanner.get_scan_status", lambda: {"ready": True})
    monkeypatch.setattr("services.watchlist_scanner._cache", {"series": [
        {"name": "Show A", "poster": "posterA", "tmdb_id": 7, "seasons": [
            {"season": 2, "episodes": [
                {"status": "upcoming", "air_date": _iso(10), "episode": 5, "name": "Future"},
                {"status": "upcoming", "air_date": _iso(-1), "episode": 4, "name": "Recent"},
                {"status": "upcoming", "air_date": _iso(-5), "episode": 3, "name": "TooOld"},
                {"status": "aired", "air_date": _iso(3), "episode": 6, "name": "Aired"},
                {"status": "upcoming", "air_date": "", "episode": 7, "name": "NoDate"},
            ]},
        ]},
    ]})
    r = await authed_client.get(_UPCOMING)
    assert r.status_code == 200
    body = r.json()
    # Only the two in-window upcoming episodes survive, sorted by air_date asc.
    assert [e["episode_name"] for e in body] == ["Recent", "Future"]
    assert body[0] == {
        "series_name": "Show A",
        "poster": "posterA",
        "tmdb_id": 7,
        "season": 2,
        "episode": 4,
        "episode_name": "Recent",
        "air_date": _iso(-1),
    }


@pytest.mark.asyncio
async def test_upcoming_caps_at_30_keeping_earliest(authed_client, monkeypatch):
    episodes = [
        {"status": "upcoming", "air_date": _iso(i + 1), "episode": i, "name": f"Ep{i}"}
        for i in range(35)
    ]
    monkeypatch.setattr("services.watchlist_scanner.get_scan_status", lambda: {"ready": True})
    monkeypatch.setattr("services.watchlist_scanner._cache", {"series": [
        {"name": "Show", "poster": "p", "tmdb_id": 1, "seasons": [{"season": 1, "episodes": episodes}]},
    ]})
    r = await authed_client.get(_UPCOMING)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 30
    # The 30 earliest are kept (sorted asc, then [:30]).
    assert body[0]["air_date"] == _iso(1)
    assert body[-1]["air_date"] == _iso(30)
