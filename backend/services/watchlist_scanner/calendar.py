"""Watchlist calendar: upcoming releases per month, with a persistent cache."""
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_watchlist_data, set_watchlist_data

from ._emby import _get_all_emby_series
from ._state import _calendar_cache
from ._tmdb import _get_tmdb_key, _tmdb_season, _tmdb_series

logger = logging.getLogger("mediakeeper.watchlist.scanner")


async def get_calendar(db: AsyncSession, year: int, month: int) -> list[dict]:
    cache_key = f"{year}-{month:02d}"

    if cache_key in _calendar_cache:
        return _calendar_cache[cache_key]

    raw = await get_watchlist_data(db, f"calendar.{cache_key}")
    if raw:
        try:
            items = json.loads(raw)
            _calendar_cache[cache_key] = items
            return items
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass

    items = await _build_calendar(db, year, month)
    _calendar_cache[cache_key] = items
    await set_watchlist_data(db, f"calendar.{cache_key}", json.dumps(items))
    return items


async def refresh_calendar_month(db: AsyncSession, year: int, month: int):
    """Force regeneration of a calendar month."""
    cache_key = f"{year}-{month:02d}"
    items = await _build_calendar(db, year, month)
    _calendar_cache[cache_key] = items
    await set_watchlist_data(db, f"calendar.{cache_key}", json.dumps(items))
    return items


async def _build_calendar(db: AsyncSession, year: int, month: int) -> list[dict]:
    if not await _get_tmdb_key(db):
        return []

    ms = f"{year:04d}-{month:02d}-01"
    me = f"{year + 1:04d}-01-01" if month == 12 else f"{year:04d}-{month + 1:02d}-01"

    # Emby series in progress
    tmdb_series = []
    for s in await _get_all_emby_series(db):
        tid = s.get("ProviderIds", {}).get("Tmdb")
        if tid and s.get("Status", "") not in ("Ended",):
            tmdb_series.append({"tmdb_id": int(tid), "name": s.get("Name", ""), "series_id": s.get("Id", ""), "source": "emby"})

    # Tracked series
    from services.watchlist_tracking import get_tracked
    tracked = await get_tracked(db)
    seen = {s["tmdb_id"] for s in tmdb_series}
    for t in tracked:
        if t.get("media_type") == "tv" and t["tmdb_id"] not in seen:
            tmdb_series.append({"tmdb_id": t["tmdb_id"], "name": t.get("name", ""), "series_id": "", "source": "tracked"})
            seen.add(t["tmdb_id"])

    items = []

    for s in tmdb_series:
        try:
            d = await _tmdb_series(db, s["tmdb_id"])
            if not d:
                continue
            pp = d.get("poster_path", "")
            ov = (d.get("overview") or "")[:300]

            for si in d.get("seasons", [])[-3:]:
                sn = si.get("season_number", 0)
                if sn == 0:
                    continue
                season_data = await _tmdb_season(db, s["tmdb_id"], sn)
                if not season_data:
                    continue
                for ep in season_data.get("episodes", []):
                    ad = ep.get("air_date", "")
                    if ad and ms <= ad < me:
                        items.append({
                            "date": ad, "series_name": s["name"], "series_id": s["series_id"],
                            "tmdb_id": s["tmdb_id"], "season": sn, "episode": ep.get("episode_number", 0),
                            "episode_name": ep.get("name", ""),
                            "poster": f"https://image.tmdb.org/t/p/w300{pp}" if pp else "",
                            "emby_poster": f"/api/emby/image/{s['series_id']}" if s["series_id"] else "",
                            "source": s["source"], "overview": ov,
                            "total_seasons": d.get("number_of_seasons", 0),
                            "total_episodes": d.get("number_of_episodes", 0),
                            "first_air_date": d.get("first_air_date", ""),
                            "is_movie": False,
                        })
        except Exception as e:
            logger.debug(f"Calendrier {s['name']}: {e}")

    # Films suivis
    tracked_movies = [t for t in tracked if t.get("media_type") == "movie"]
    logger.info(f"[calendar] {len(tracked_movies)} tracked movies, period {ms} → {me}")
    for t in tracked_movies:
        rd = t.get("release_date", "")
        logger.debug(f"[calendar] Film '{t.get('name')}' release_date='{rd}' in_range={bool(rd and ms <= rd < me)}")
        if rd and ms <= rd < me:
            items.append({
                "date": rd, "series_name": t.get("name", ""), "series_id": "",
                "tmdb_id": t["tmdb_id"], "season": 0, "episode": 0,
                # No hardcoded label: the frontend renders a localized
                # "movie release" tag for movie rows (dashboard.movieRelease).
                "episode_name": "", "poster": t.get("poster", ""),
                "emby_poster": "", "source": "tracked",
                "overview": (t.get("overview") or "")[:300],
                "total_seasons": 0, "total_episodes": 0,
                "first_air_date": rd, "is_movie": True,
            })

    items.sort(key=lambda x: (x["date"], x["series_name"]))
    return items
