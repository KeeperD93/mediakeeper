"""Genre inference from Emby playback history (temporal weighting)."""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from models.user import User
from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE
from services.portal.personal_utils import (
    CATCH_ALL_GENRES,
    _HISTORY_SAMPLE,
    _playback_user_filter,
    _weight_for_age,
    _coerce_int,
)

logger = logging.getLogger("mediakeeper.portal.personal")


async def _sample_latest_plays(
    db: AsyncSession, user: User, profile: UserProfile,
) -> dict[str, tuple[str, datetime]]:
    """
    Return ``{emby_id: (media_type, started_at)}`` for the user's most
    recent plays, de-duplicated so each item appears once with its
    latest timestamp. Empty dict when history is empty or the query
    fails. Shared between ``_infer_genres_from_history`` variants.
    """
    stmt = (
        select(
            PlaybackSession.item_id,
            PlaybackSession.item_type,
            PlaybackSession.started_at,
        )
        .where(_playback_user_filter(user, profile))
        .order_by(desc(PlaybackSession.started_at))
        .limit(_HISTORY_SAMPLE)
    )
    try:
        rows = (await db.execute(stmt)).all()
    except Exception as e:
        logger.debug("[PERSONAL] history query failed: %s", e)
        return {}

    latest_seen: dict[str, tuple[str, datetime]] = {}
    for r in rows:
        mtype = "tv" if r.item_type == "Episode" else "movie"
        existing = latest_seen.get(r.item_id)
        if existing is None or r.started_at > existing[1]:
            latest_seen[r.item_id] = (mtype, r.started_at)
    return latest_seen


async def _resolve_emby_to_tmdb(
    db: AsyncSession, emby_ids: list[str],
) -> dict[str, tuple[int, str]]:
    """Map ``emby_id → (tmdb_id, media_type)`` via the index table."""
    if not emby_ids:
        return {}
    rows = (await db.execute(
        select(EmbyTmdbIndex).where(EmbyTmdbIndex.emby_item_id.in_(emby_ids))
    )).scalars().all()
    return {r.emby_item_id: (r.tmdb_id, r.media_type) for r in rows}


async def _fetch_genres_per_play(
    db: AsyncSession,
    latest_seen: dict[str, tuple[str, datetime]],
    tmdb_map: dict[str, tuple[int, str]],
) -> tuple[Counter, Counter]:
    """
    Walk each (emby_id → started_at) entry, fetch TMDB genres and apply
    temporal weighting. Returns ``(primary, fallback)`` counters where
    primary excludes CATCH_ALL_GENRES and fallback includes them only.
    """
    api_key = await _get_tmdb_key(db)
    if not api_key:
        return Counter(), Counter()

    client = get_external_client()
    primary: Counter[int] = Counter()
    fallback: Counter[int] = Counter()
    now = datetime.now(timezone.utc)

    for emby_id, (mtype, started_at) in latest_seen.items():
        entry = tmdb_map.get(emby_id)
        if not entry:
            continue
        tmdb_id, _ = entry
        weight = _weight_for_age(now, started_at)
        try:
            res = await client.get(
                f"{TMDB_BASE}/{mtype}/{tmdb_id}",
                params={"language": "en-US"},
                headers=_tmdb_headers_sync(api_key),
            )
            if res.status_code != 200:
                continue
            for g in (res.json() or {}).get("genres", []):
                gid = _coerce_int(g.get("id"))
                if not gid:
                    continue
                if gid in CATCH_ALL_GENRES:
                    fallback[gid] += weight
                else:
                    primary[gid] += weight
        except Exception:  # noqa: S112 -- intentional best-effort iteration, skip individual failure
            continue
    return primary, fallback


async def _infer_genres_from_history(
    db: AsyncSession, user: User, profile: UserProfile,
) -> list[int]:
    """
    Look at the user's recent Emby plays, resolve them to TMDB ids via
    ``emby_tmdb_index``, fetch their genre ids from TMDB, then rank them
    with temporal weighting (recent plays count more than old ones).

    Catch-all genres (mainly Drama) are excluded from the primary ranking
    because they match almost everything. They are kept as a fallback so
    the row is not empty when a user has ONLY catch-all history.
    """
    latest_seen = await _sample_latest_plays(db, user, profile)
    if not latest_seen:
        return []

    tmdb_map = await _resolve_emby_to_tmdb(db, list(latest_seen.keys()))
    primary, fallback = await _fetch_genres_per_play(db, latest_seen, tmdb_map)

    if primary:
        return [gid for gid, _ in primary.most_common(3)]
    return [gid for gid, _ in fallback.most_common(3)]


async def _infer_genres_from_history_full(
    db: AsyncSession, user: User, profile: UserProfile,
) -> tuple[list[int], Counter]:
    """
    Like ``_infer_genres_from_history`` but also returns the full raw
    counter (including catch-all genres) so the caller can compute
    genre-percentage stats. Returns
    ``(primary_genre_ids, full_counter_including_catchall)``.
    """
    latest_seen = await _sample_latest_plays(db, user, profile)
    if not latest_seen:
        return [], Counter()

    tmdb_map = await _resolve_emby_to_tmdb(db, list(latest_seen.keys()))
    primary, fallback = await _fetch_genres_per_play(db, latest_seen, tmdb_map)

    all_genres = primary + fallback
    if primary:
        return [gid for gid, _ in primary.most_common(5)], all_genres
    return [gid for gid, _ in all_genres.most_common(5)], all_genres
