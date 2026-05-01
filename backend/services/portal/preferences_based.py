"""User-preferences discover — powers the "Based on your preferences"
carousel and its paginated category page.

The user ticks a list of favourite genres in their Portal profile
(both movie and TV genre ids are stored together in
``UserProfile.favorite_genres``). This module asks TMDB Discover for
both /movie and /tv items filtered by those genres, merges and sorts
them by popularity desc, and returns a paginated slice.
"""
from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from services.portal.discover import _fetch_list_params
from services.portal.personal import _get_indexed_tmdb_ids

logger = logging.getLogger("mediakeeper.portal.preferences")

# Genre ids that only make sense for movies vs TV — used to split the
# user's ticked genres before calling /discover/{movie,tv}.
_TV_ONLY_GENRES = {10759, 10762, 10763, 10764, 10765, 10766, 10767, 10768}
_MOVIE_ONLY_GENRES = {28, 12, 80, 14, 36, 10749, 10752, 37, 53}

PAGE_SIZE = 40


async def get_preferences_based(
    db: AsyncSession, profile: UserProfile, page: int = 1,
) -> dict:
    """Merged movie + TV Discover filtered by the user's ticked genres."""
    raw_genres = profile.favorite_genres or []
    try:
        genre_ids = [int(g) for g in raw_genres if str(g).lstrip("-").isdigit()]
    except Exception:
        genre_ids = []
    if not genre_ids:
        return {"items": [], "page": page, "has_more": False}

    movie_genres = [g for g in genre_ids if g not in _TV_ONLY_GENRES]
    tv_genres = [g for g in genre_ids if g not in _MOVIE_ONLY_GENRES]

    include_adult = not bool(profile.hide_adult)
    # Pull two TMDB pages per media type so the merged pool is dense
    # enough to paginate server-side without another round-trip.
    tmdb_page_start = (page - 1) * 2 + 1

    async def _pull(mt: str, gids: list[int]) -> list[dict]:
        if not gids:
            return []
        # OR semantics — ``,`` would force TMDB to return only items
        # tagged with EVERY ticked genre, which collapses to nothing as
        # soon as the user picks 3+ categories. ``|`` is the OR
        # operator and matches "any of the genres I like".
        params = {
            "with_genres": "|".join(str(g) for g in gids),
            "sort_by": "popularity.desc",
            "vote_count.gte": "100",
        }
        out: list[dict] = []
        for tp in (tmdb_page_start, tmdb_page_start + 1):
            part = await _fetch_list_params(
                db, f"/discover/{mt}", tp, params,
                include_adult=include_adult,
            )
            out.extend(part)
        return out

    movies = await _pull("movie", movie_genres)
    tv = await _pull("tv", tv_genres)

    idx_m = await _get_indexed_tmdb_ids(db, "movie")
    idx_t = await _get_indexed_tmdb_ids(db, "tv")

    # Merge movies + TV, de-dupe, sort by popularity desc, and mark
    # already-indexed items so the card can show the green dot right
    # away (no second request-status round-trip needed).
    pool: dict[tuple[int, str], dict] = {}
    for it in movies + tv:
        tid = it.get("tmdb_id")
        mt = it.get("media_type")
        if not tid or not mt:
            continue
        key = (tid, mt)
        if key in pool:
            continue
        if mt == "movie" and tid in idx_m:
            it["availability"] = "full"
        elif mt == "tv" and tid in idx_t:
            it["availability"] = "full"
        pool[key] = it

    merged = sorted(pool.values(), key=lambda x: x.get("popularity", 0), reverse=True)

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    items = merged[start:end]
    has_more = len(merged) > end
    return {"items": items, "page": page, "has_more": has_more}
