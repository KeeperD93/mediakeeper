"""
"Recommended for you" rows for the Portal home.

Blends declared favorite genres with genres inferred from recent playback
history, queries TMDB discover in parallel for both movies and TV, excludes
items already present in the Emby library, respects the hide_adult profile
preference, and interleaves movie + TV results.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from services.portal.discover import _fetch_list_params
from services.portal.personal_utils import (
    _coerce_int,
    _interleave,
    _get_indexed_tmdb_ids,
    _count_total_plays,
)
from services.portal.personal_genres import (
    _infer_genres_from_history,
    _infer_genres_from_history_full,
)

logger = logging.getLogger("mediakeeper.portal.personal")


async def get_recommendations_for_user(
    db: AsyncSession, user: User, profile: UserProfile,
) -> list[dict]:
    """
    Build "Recommended for you" row by:

    1. Blending the user's declared favorite genres with genres inferred
       from their recent Emby playback history (temporal weighting,
       catch-all genres excluded from the ranking).
    2. Querying TMDB ``/discover/movie`` AND ``/discover/tv`` in parallel.
    3. Filtering out items already present in ``emby_tmdb_index``.
    4. Respecting ``profile.hide_adult``.
    5. Interleaving the movie and TV results so both are represented.

    Returns an empty list when there is no usable genre signal — the
    frontend hides the whole row in that case.
    """
    declared = [
        gid for g in (profile.favorite_genres or [])
        if (gid := _coerce_int(g)) is not None
    ]

    inferred = await _infer_genres_from_history(db, user, profile)

    # Merge declared first (user intent), then inferred (observed),
    # dedupe while preserving order. Cap at 3 to keep TMDB results tight.
    merged: list[int] = []
    for gid in (*declared, *inferred):
        if gid not in merged:
            merged.append(gid)
        if len(merged) >= 3:
            break

    if not merged:
        logger.info(
            f"[PERSONAL] recommended empty for user={user.username!r} "
            f"profile={profile.display_name!r}: no declared genres and no inferred history"
        )
        return []

    include_adult = not bool(profile.hide_adult)
    # OR semantics — TMDB ``,`` is AND (must contain ALL genres), which
    # collapses to nothing as soon as the merged top-3 spans
    # incompatible categories (e.g. War + Politics + Western for a user
    # who watches a bit of everything). ``|`` is OR and gives a usable
    # popularity-sorted feed across the user's actual interests.
    discover_params = {
        "with_genres": "|".join(str(g) for g in merged),
        "sort_by": "popularity.desc",
        "vote_count.gte": "300",
    }

    movies, tv, indexed_movies, indexed_tv = await asyncio.gather(
        _fetch_list_params(db, "/discover/movie", 1, discover_params, include_adult=include_adult),
        _fetch_list_params(db, "/discover/tv", 1, discover_params, include_adult=include_adult),
        _get_indexed_tmdb_ids(db, "movie"),
        _get_indexed_tmdb_ids(db, "tv"),
    )

    movies = [m for m in movies if m.get("tmdb_id") not in indexed_movies]
    tv = [t for t in tv if t.get("tmdb_id") not in indexed_tv]

    return _interleave(movies, tv, max_n=20)


async def get_recommendations_premium(
    db: AsyncSession, user: User, profile: UserProfile,
) -> dict:
    """
    Enriched recommendations for the dedicated premium page.

    Returns up to 60 items (3 pages from TMDB) plus playback stats so the
    frontend can build a curated, genre-grouped experience. Items carry
    their ``genres`` field (list of TMDB genre IDs) — the frontend groups
    them by primary genre and labels each section via i18n mappings.
    """
    declared = [
        gid for g in (profile.favorite_genres or [])
        if (gid := _coerce_int(g)) is not None
    ]
    inferred_primary, inferred_all = await _infer_genres_from_history_full(db, user, profile)

    merged: list[int] = []
    for gid in (*declared, *inferred_primary):
        if gid not in merged:
            merged.append(gid)
        if len(merged) >= 5:
            break

    total_plays = await _count_total_plays(db, user, profile)
    total_weight = sum(inferred_all.values()) or 1
    genre_stats = [
        {"id": gid, "percentage": round(100 * w / total_weight)}
        for gid, w in inferred_all.most_common(6)
    ]

    if not merged:
        return {
            "hero": None,
            "stats": {"total_plays": total_plays, "top_genres": genre_stats},
            "items": [],
            "genre_ids": [],
        }

    include_adult = not bool(profile.hide_adult)
    discover_params = {
        "with_genres": ",".join(str(g) for g in merged),
        "sort_by": "popularity.desc",
        "vote_count.gte": "200",
    }

    # Page 1: same pattern as get_recommendations_for_user — 4 tasks
    # sharing the DB session, proven to work.
    movies, tv, idx_m, idx_t = await asyncio.gather(
        _fetch_list_params(db, "/discover/movie", 1, discover_params, include_adult=include_adult),
        _fetch_list_params(db, "/discover/tv", 1, discover_params, include_adult=include_adult),
        _get_indexed_tmdb_ids(db, "movie"),
        _get_indexed_tmdb_ids(db, "tv"),
    )

    movies = [m for m in movies if m.get("tmdb_id") not in idx_m]
    tv = [t for t in tv if t.get("tmdb_id") not in idx_t]

    # Pages 2-3: fetch sequentially to avoid concurrent DB session issues.
    # (asyncio.gather with nested _fetch_list_params calls on the same
    # session can break SQLAlchemy async.)
    for page in (2, 3):
        if len(movies) + len(tv) >= 60:
            break
        m2 = await _fetch_list_params(
            db, "/discover/movie", page, discover_params, include_adult=include_adult,
        )
        t2 = await _fetch_list_params(
            db, "/discover/tv", page, discover_params, include_adult=include_adult,
        )
        movies.extend(m for m in m2 if m.get("tmdb_id") not in idx_m)
        tv.extend(t for t in t2 if t.get("tmdb_id") not in idx_t)

    items = _interleave(movies, tv, max_n=60)
    hero = items[0] if items else None

    return {
        "hero": hero,
        "stats": {"total_plays": total_plays, "top_genres": genre_stats},
        "items": items,
        "genre_ids": merged,
    }
