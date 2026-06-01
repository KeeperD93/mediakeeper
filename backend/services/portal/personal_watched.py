"""
"Because you watched X" row — TMDB recommendations based on the
user's most recent Emby playback.

Resolves the pivot (movie or series) from the playback history, then
fetches TMDB recommendations for it. Returns an empty structure when
the user has no playback history or when the index lookup fails — the
frontend hides the row in that case.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from models.user import User
from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE
from services.portal.discover import _normalize
from services.portal.runtime_cache import resolve_runtimes
from services.portal.personal_utils import (
    _LATEST_POOL,
    _playback_user_filter,
)

# When a media-type filter is set we have to scan further back than the
# default pool (which only keeps the single most recent play): users
# who've been binge-watching a series might have dozens of episode rows
# before the last movie row appears.
_FILTERED_POOL = 200

logger = logging.getLogger("mediakeeper.portal.personal")


async def get_because_you_watched(
    db: AsyncSession, user: User, profile: UserProfile,
    media_type_filter: str | None = None,
) -> dict:
    """
    Returns ``{"pivot": {...}, "items": [...]}`` where ``pivot`` is the
    TMDB-normalised last-watched media and ``items`` are TMDB
    recommendations for it. When the user has no history at all, both
    fields are empty so the frontend can hide the row.

    ``media_type_filter`` restricts the pivot search to either ``movie``
    or ``tv`` so the profile page can show one carousel per media type.
    """
    empty = {"pivot": None, "items": []}

    # Pull a larger slice of recent plays so we can scan for the first
    # row whose media_type matches the filter (or the first one at all
    # when no filter is passed).
    stmt = (
        select(
            PlaybackSession.item_id,
            PlaybackSession.item_name,
            PlaybackSession.item_type,
            PlaybackSession.series_name,
            PlaybackSession.started_at,
        )
        .where(_playback_user_filter(user, profile))
        .order_by(desc(PlaybackSession.started_at))
        .limit(_FILTERED_POOL if media_type_filter else _LATEST_POOL)
    )
    try:
        rows = (await db.execute(stmt)).all()
    except Exception as e:
        logger.debug(f"[PERSONAL] latest play query failed: {e}")
        return empty

    if not rows:
        return empty

    # Pick the first row whose resolved media_type matches the filter.
    # For ``tv`` the pivot can come from either an Episode row or a
    # Movie row pointing to a Series via the Emby index (rare but safe).
    tmdb_id = None
    media_type = None
    pivot_title = None
    for row in rows:
        is_episode = row.item_type == "Episode"
        want_tv = media_type_filter == "tv"
        want_movie = media_type_filter == "movie"
        if want_tv and not is_episode:
            continue
        if want_movie and is_episode:
            continue
        if is_episode:
            series_row = await _find_series_index_entry(db, row.series_name)
            if not series_row:
                continue
            tmdb_id = series_row.tmdb_id
            media_type = "tv"
            pivot_title = row.series_name or row.item_name
        else:
            idx_row = await db.execute(
                select(EmbyTmdbIndex).where(EmbyTmdbIndex.emby_item_id == row.item_id)
            )
            entry = idx_row.scalar_one_or_none()
            if not entry:
                continue
            if want_movie and entry.media_type != "movie":
                continue
            tmdb_id = entry.tmdb_id
            media_type = entry.media_type
            pivot_title = row.item_name
        break

    if tmdb_id is None:
        return empty

    items = await _fetch_recommendations(db, media_type, tmdb_id)
    if not items:
        return empty

    return {
        "pivot": {
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "title": pivot_title,
        },
        "items": items,
    }


async def _find_series_index_entry(
    db: AsyncSession, series_name: Optional[str],
):
    """
    Lookup a series in ``emby_tmdb_index`` by its title. The playback row
    only gives us the series *name* (not id), so we have to match on
    string. Titles can differ between Emby's display language and what's
    stored in the index, so we do a best-effort cascade:

      1. Exact case-insensitive match — the common case.
      2. Substring match in either direction — handles punctuation drops
         ("Dr. Stone" vs "Dr Stone") and suffixes like "(2024)" appended
         to the Emby title.

    Returns the first ``media_type == 'tv'`` hit, or ``None``.
    """
    if not series_name:
        return None

    clean = series_name.strip()
    if not clean:
        return None

    # 1. Exact case-insensitive match
    stmt = (
        select(EmbyTmdbIndex)
        .where(
            EmbyTmdbIndex.media_type == "tv",
            func.lower(EmbyTmdbIndex.title) == clean.lower(),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row:
        return row

    # 2. Loose substring match (handles "Dr. Stone" ↔ "Dr Stone",
    #    "Show Name (2024)" ↔ "Show Name", etc.)
    like = f"%{clean}%"
    stmt = (
        select(EmbyTmdbIndex)
        .where(
            EmbyTmdbIndex.media_type == "tv",
            EmbyTmdbIndex.title.ilike(like),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row:
        return row

    # 3. Reverse substring: maybe the Emby title is a prefix of the
    #    TMDB title (or vice versa). Pick the shortest candidate to
    #    minimise false positives.
    stmt = (
        select(EmbyTmdbIndex)
        .where(
            EmbyTmdbIndex.media_type == "tv",
            func.lower(EmbyTmdbIndex.title).like(func.lower(clean).concat("%")),
        )
        .order_by(func.length(EmbyTmdbIndex.title))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _fetch_recommendations(
    db: AsyncSession, media_type: str, tmdb_id: int,
) -> list[dict]:
    api_key = await _get_tmdb_key(db)
    if not api_key:
        return []
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}/recommendations",
            params={"language": "en-US", "page": 1},
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return []
        results = (res.json() or {}).get("results") or []
        recs = [_normalize(r) for r in results[:20]]
        await resolve_runtimes(recs)
        return recs
    except Exception as e:
        logger.debug(f"[PERSONAL] recommendations fetch failed: {e}")
        return []
