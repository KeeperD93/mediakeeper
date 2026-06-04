"""Per-locale localization contract for GET /api/watchlist/scan and
/api/watchlist/calendar.

The scan/calendar caches are built once in the default language. A viewer
whose locale differs (via the ``X-MK-Locale`` header) gets the display fields
re-resolved from TMDB (stubbed here), while the default locale is served as-is
and the cached blob is never mutated.
"""
from __future__ import annotations

import pytest

_SCAN = "/api/watchlist/scan"
_CAL = "/api/watchlist/calendar"


async def _fake_series(db, tmdb_id, lang):
    return {
        "name": f"Show{tmdb_id} [{lang}]",
        "poster_path": f"/p{tmdb_id}.jpg",
        "overview": f"Overview{tmdb_id} [{lang}]",
        "seasons": [{"season_number": 1, "name": f"Season1 [{lang}]"}],
    }


async def _fake_season(db, tmdb_id, sn, lang):
    return {"episodes": [{"episode_number": e, "name": f"S{sn}E{e} [{lang}]"} for e in range(1, 4)]}


async def _fake_key(db=None):
    return "test-key"


def _patch_tmdb(monkeypatch):
    monkeypatch.setattr("services.watchlist_scanner._localize._get_tmdb_key", _fake_key)
    monkeypatch.setattr("services.watchlist_scanner._tmdb._tmdb_series", _fake_series)
    monkeypatch.setattr("services.watchlist_scanner._tmdb._tmdb_season", _fake_season)


def _scan_blob() -> dict:
    return {
        "series": [{
            "tmdb_id": 7, "name": "Emby A", "poster": "/old.jpg", "overview": "vieux fr",
            "seasons": [{"season": 1, "name": "Saison 1", "episodes": [
                {"episode": 1, "name": "ancien", "status": "missing", "air_date": "2030-01-01"},
            ]}],
        }],
        "total_missing": 1, "total_upcoming": 0, "scan_time": 1,
    }


def _cal_items() -> list[dict]:
    return [
        {"date": "2030-01-05", "series_name": "Emby A", "tmdb_id": 7, "season": 1, "episode": 1,
         "episode_name": "ancien", "poster": "/old.jpg", "overview": "vieux", "is_movie": False},
        {"date": "2030-01-10", "series_name": "Film X", "tmdb_id": 99, "season": 0, "episode": 0,
         "episode_name": "Sortie film", "poster": "", "overview": "", "is_movie": True},
    ]


def _patch_scan(monkeypatch, blob):
    async def _fake(db):
        return blob
    monkeypatch.setattr("api.watchlist.get_scan_results", _fake)


def _patch_calendar(monkeypatch, items):
    async def _fake(db, year, month):
        return items
    monkeypatch.setattr("api.watchlist.get_calendar", _fake)


@pytest.mark.asyncio
async def test_scan_default_locale_served_as_is(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    _patch_scan(monkeypatch, _scan_blob())
    r = await authed_client.get(_SCAN)  # no header -> default locale, no re-resolution
    assert r.status_code == 200
    s = r.json()["series"][0]
    assert s["name"] == "Emby A"
    assert s["seasons"][0]["episodes"][0]["name"] == "ancien"


@pytest.mark.asyncio
async def test_scan_localizes_to_viewer_language(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    _patch_scan(monkeypatch, _scan_blob())
    r = await authed_client.get(_SCAN, headers={"X-MK-Locale": "en"})
    assert r.status_code == 200
    s = r.json()["series"][0]
    assert s["name"] == "Show7 [en-US]"
    assert s["poster"] == "https://image.tmdb.org/t/p/w300/p7.jpg"
    assert s["overview"] == "Overview7 [en-US]"
    assert s["seasons"][0]["name"] == "Season1 [en-US]"
    assert s["seasons"][0]["episodes"][0]["name"] == "S1E1 [en-US]"


@pytest.mark.asyncio
async def test_scan_does_not_mutate_cached_blob(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    blob = _scan_blob()
    _patch_scan(monkeypatch, blob)
    await authed_client.get(_SCAN, headers={"X-MK-Locale": "en"})
    # The shared cache object must survive a per-request localization untouched.
    assert blob["series"][0]["name"] == "Emby A"
    assert blob["series"][0]["seasons"][0]["episodes"][0]["name"] == "ancien"


@pytest.mark.asyncio
async def test_scan_no_tmdb_key_serves_cache(authed_client, monkeypatch):
    # No TMDB key: cannot re-resolve, so the cache is served untouched even for a
    # non-default locale -- and no concurrent DB access is attempted on the session.
    async def _no_key(db=None):
        return ""
    monkeypatch.setattr("services.watchlist_scanner._localize._get_tmdb_key", _no_key)
    _patch_scan(monkeypatch, _scan_blob())
    r = await authed_client.get(_SCAN, headers={"X-MK-Locale": "en"})
    assert r.status_code == 200
    assert r.json()["series"][0]["name"] == "Emby A"


@pytest.mark.asyncio
async def test_calendar_localizes_tv_keeps_movies(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    _patch_calendar(monkeypatch, _cal_items())
    r = await authed_client.get(_CAL, params={"year": 2030, "month": 1}, headers={"X-MK-Locale": "en"})
    assert r.status_code == 200
    body = r.json()
    tv = next(i for i in body if not i["is_movie"])
    movie = next(i for i in body if i["is_movie"])
    assert tv["series_name"] == "Show7 [en-US]"
    assert tv["episode_name"] == "S1E1 [en-US]"
    # Movie row left untouched (needs the /movie endpoint, deferred).
    assert movie["series_name"] == "Film X"
    assert movie["episode_name"] == "Sortie film"


@pytest.mark.asyncio
async def test_calendar_default_locale_served_as_is(authed_client, monkeypatch):
    _patch_tmdb(monkeypatch)
    _patch_calendar(monkeypatch, _cal_items())
    r = await authed_client.get(_CAL, params={"year": 2030, "month": 1})
    assert r.status_code == 200
    assert r.json()[0]["series_name"] == "Emby A"  # no re-resolution at default
