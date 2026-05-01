"""Most-rewatched movie / series computation — pulls authoritative
PlayCount from Emby's per-user UserData for the strongest signal.
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.playback_stats import PlaybackSession

logger = logging.getLogger("mediakeeper.portal.profile_stats")


async def compute_most_rewatched(
    db: AsyncSession, user_filter, excl_filters: list,
) -> tuple[dict | None, dict | None, dict | None]:
    """Returns ``(any, movie, series)`` rewatch winners.

    Movie rewatch count: pulled directly from Emby's per-user
    ``UserData.PlayCount`` for the top candidates. PlayCount only
    increments when Emby considers a play complete, which is exactly
    what the user thinks of as a "real" rewatch.

    Series rewatch count: ``min(UserData.PlayCount)`` across the
    available non-special episodes — a series only counts as one
    rewatch once every episode of every available season has been
    played (so adding a new unplayed season doesn't reset the floor,
    and watching only that new season doesn't grant another rewatch).

    Falls back to the local ``complete_views`` accounting (live + legacy
    plugin sessions) when no Emby user id can be resolved.
    """
    from services.portal.profile_stats_emby import (
        _find_series_emby_id, resolve_emby_user_id,
    )
    from services.portal.profile_stats_completion import (
        aggregate_play_signal, complete_views, fetch_runtimes,
    )
    from services.settings import get_active_media_source

    source = await get_active_media_source(db)
    emby_url = emby_key = ""
    if source and source.get("source") in ("emby", "jellyfin"):
        emby_url = source.get("url", "").rstrip("/")
        emby_key = source.get("api_key", "")
    emby_uid = await resolve_emby_user_id(db, user_filter)

    try:
        rows = (await db.execute(
            select(
                PlaybackSession.item_type, PlaybackSession.item_id,
                PlaybackSession.item_name, PlaybackSession.series_name,
                PlaybackSession.position_ticks, PlaybackSession.duration_ticks,
            ).where(user_filter, *excl_filters)
        )).all()
    except Exception as e:
        logger.debug(f"[PROFILE] most rewatched fetch error: {e}")
        return None, None, None

    movie_rows = [r for r in rows if r.item_type == "Movie" and r.item_id]
    ep_rows = [r for r in rows if r.item_type == "Episode" and r.item_id and r.series_name]

    movie_meta: dict[str, dict] = {}
    for r in movie_rows:
        movie_meta.setdefault(r.item_id, {"title": r.item_name})
    series_meta: dict[str, set] = {}
    for r in ep_rows:
        series_meta.setdefault(r.series_name, set()).add(r.item_id)

    movie_agg = aggregate_play_signal(movie_rows)
    ep_agg = aggregate_play_signal(ep_rows)

    # Movies — short-list by raw signal then ask Emby for the
    # authoritative PlayCount per item (UserData reflects "Mark as
    # played" actions and Emby's own completion threshold).
    def _signal(d):
        return d.get("complete_sessions", 0) * 10**12 + d.get("residual_ticks", 0)
    movie_candidates = sorted(
        movie_meta.keys(),
        key=lambda mid: _signal(movie_agg.get(mid, {})),
        reverse=True,
    )[:25]

    most_rewatched_movie = None
    best_movie_count = 1
    if movie_candidates and emby_url and emby_uid:
        try:
            res = await get_internal_client().get(
                f"{emby_url}/Users/{emby_uid}/Items",
                params={"Ids": ",".join(movie_candidates), "Fields": "UserData"},
                headers={"X-Emby-Token": emby_key}, timeout=10.0,
            )
            payload = res.json().get("Items", []) if res.status_code == 200 else []
        except Exception:
            payload = []
        for item in payload:
            mid = item.get("Id")
            ud = item.get("UserData") or {}
            pc = int(ud.get("PlayCount") or 0)
            if pc > best_movie_count:
                best_movie_count = pc
                most_rewatched_movie = {
                    "title": movie_meta.get(mid, {}).get("title") or item.get("Name", ""),
                    "count": pc,
                    "poster_url": f"/api/emby/image/{mid}?type=Primary",
                }
    elif movie_candidates and emby_url:
        # Fallback: local complete_views maths
        movie_runtimes = await fetch_runtimes(movie_candidates, emby_url, emby_key)
        for mid in movie_candidates:
            c = complete_views(mid, movie_runtimes.get(mid, 0), movie_agg)
            if c > best_movie_count:
                best_movie_count = c
                most_rewatched_movie = {
                    "title": movie_meta[mid]["title"], "count": c,
                    "poster_url": f"/api/emby/image/{mid}?type=Primary",
                }

    # Series — for the top 8 candidates by raw episode play volume,
    # ask Emby for the authoritative episode list (excluding Specials
    # + Virtual) and compute the min across those.
    series_candidates = sorted(
        series_meta.keys(),
        key=lambda sn: sum(_signal(ep_agg.get(eid, {})) for eid in series_meta[sn]),
        reverse=True,
    )[:8]

    # Resolve series id + fetch episode list in parallel for all 8
    # candidates — cuts ~16 sequential Emby HTTP calls down to 2
    # concurrent rounds, saving ~1-1.5 s on the profile-full latency.
    async def _series_min_views(sn: str):
        if not emby_url:
            return None
        series_emby_id = await _find_series_emby_id(sn, emby_url, emby_key)
        if not series_emby_id:
            return None
        params = {"Fields": "LocationType,ParentIndexNumber,RunTimeTicks,UserData"}
        if emby_uid:
            params["UserId"] = emby_uid
        try:
            res = await get_internal_client().get(
                f"{emby_url}/Shows/{series_emby_id}/Episodes",
                params=params,
                headers={"X-Emby-Token": emby_key},
                timeout=10.0,
            )
            if res.status_code != 200:
                return None
            eps = res.json().get("Items", []) or []
        except Exception:
            return None
        available = [
            e for e in eps
            if e.get("Id")
            and (e.get("LocationType") or "") != "Virtual"
            and e.get("ParentIndexNumber") not in (0, None)
        ]
        if not available:
            return None
        if emby_uid:
            min_views = min(
                int((e.get("UserData") or {}).get("PlayCount") or 0)
                for e in available
            )
        else:
            min_views = min(
                complete_views(e.get("Id"), int(e.get("RunTimeTicks") or 0), ep_agg)
                for e in available
            )
        return sn, series_emby_id, min_views

    most_rewatched_series = None
    best_series_count = 1
    if series_candidates and emby_url:
        results = await asyncio.gather(
            *[_series_min_views(sn) for sn in series_candidates],
            return_exceptions=False,
        )
        for r in results:
            if not r:
                continue
            sn, series_emby_id, min_views = r
            if min_views > best_series_count:
                best_series_count = min_views
                most_rewatched_series = {
                    "title": sn, "count": min_views,
                    "poster_url": f"/api/emby/image/{series_emby_id}?type=Primary",
                }

    most_rewatched = most_rewatched_movie or most_rewatched_series
    return most_rewatched, most_rewatched_movie, most_rewatched_series
