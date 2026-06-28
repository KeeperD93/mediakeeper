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
)
from services.portal.personal_genres import (
    _infer_genres_from_history,
)

logger = logging.getLogger("mediakeeper.portal.personal")


async def get_recommendations_for_user(
    db: AsyncSession, user: User, profile: UserProfile,
    *, locale: str | None = None,
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
        _fetch_list_params(
            db, "/discover/movie", 1, discover_params,
            include_adult=include_adult, language=locale,
        ),
        _fetch_list_params(
            db, "/discover/tv", 1, discover_params,
            include_adult=include_adult, language=locale,
        ),
        _get_indexed_tmdb_ids(db, "movie"),
        _get_indexed_tmdb_ids(db, "tv"),
    )

    movies = [m for m in movies if m.get("tmdb_id") not in indexed_movies]
    tv = [t for t in tv if t.get("tmdb_id") not in indexed_tv]

    # Page-1 popular titles in the user's favourite genres are usually
    # already in the library and get filtered out here, leaving the row
    # short of 20 — the one row that filters against the index. Pull a few
    # more pages (sequentially — concurrent nested fetches on the same
    # session break SQLAlchemy async), skipping indexed and already-kept
    # ids so the row reaches 20 distinct items.
    seen_movies = {m.get("tmdb_id") for m in movies}
    seen_tv = {t.get("tmdb_id") for t in tv}
    for page in (2, 3):
        if len(movies) + len(tv) >= 20:
            break
        more_movies = await _fetch_list_params(
            db, "/discover/movie", page, discover_params,
            include_adult=include_adult, language=locale,
        )
        more_tv = await _fetch_list_params(
            db, "/discover/tv", page, discover_params,
            include_adult=include_adult, language=locale,
        )
        for m in more_movies:
            mid = m.get("tmdb_id")
            if mid not in indexed_movies and mid not in seen_movies:
                movies.append(m)
                seen_movies.add(mid)
        for t in more_tv:
            tid = t.get("tmdb_id")
            if tid not in indexed_tv and tid not in seen_tv:
                tv.append(t)
                seen_tv.add(tid)

    return _interleave(movies, tv, max_n=20)
