"""Viewing-pattern stats: genre breakdown, marathon chains, movie/series
ratio, time-of-day buckets, weekday distribution.
"""
import logging
from collections import Counter
from datetime import timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from services.portal._watch_threshold import session_meets_threshold
from services.portal.personal import _infer_genres_from_history_full
from services.portal.personal_utils import TMDB_GENRE_NAME_TO_ID

logger = logging.getLogger("mediakeeper.portal.profile_stats")

MARATHON_GAP_SECONDS = 30 * 60  # two sessions within 30 min count as the same chain


async def compute_genre_stats(
    db: AsyncSession, user, profile, user_filter=None, excl_filters=None,
) -> list[dict]:
    """Top 8 genres with percentage.

    First tries an instant aggregation of PlaybackSession.genres across the
    user's full history (Emby's CSV genre names → TMDB ids via
    TMDB_GENRE_NAME_TO_ID). When that column is empty (old sessions before
    genre collection) or unmapped, falls back to the sampled + TMDB-fetched
    inference so newer users and legacy users both get stats."""
    # Build a case-insensitive name → id lookup once per call
    name_to_id_ci = {k.lower(): v for k, v in TMDB_GENRE_NAME_TO_ID.items()}
    try:
        from services.portal.personal import _playback_user_filter
        uf = user_filter if user_filter is not None else _playback_user_filter(user, profile)
        excl = excl_filters or []
        # Walk individual rows so we can dedupe by media before
        # crediting genres. Counting raw sessions would let a series
        # with 100 episodes outweigh a film 100×; the rule is +1 per
        # unique (user × media) once the watch threshold is crossed.
        rows = await db.execute(
            select(
                PlaybackSession.item_id,
                PlaybackSession.item_type,
                PlaybackSession.series_name,
                PlaybackSession.genres,
                PlaybackSession.position_ticks,
                PlaybackSession.duration_ticks,
            )
            .where(
                uf,
                PlaybackSession.genres.isnot(None),
                PlaybackSession.genres != "",
                *excl,
            )
        )
        seen_keys: set[tuple[str, str]] = set()
        counter: Counter[int] = Counter()
        for row in rows.all():
            if not session_meets_threshold(row.position_ticks, row.duration_ticks):
                continue
            if row.item_type == "Episode" and row.series_name:
                key = ("series", row.series_name)
            else:
                key = ("item", row.item_id or "")
            if not key[1] or key in seen_keys:
                continue
            seen_keys.add(key)
            for raw in (row.genres or "").split(","):
                gid = name_to_id_ci.get(raw.strip().lower())
                if gid:
                    counter[gid] += 1
        if counter:
            total = sum(counter.values()) or 1
            return [
                {"id": gid, "percentage": round(100 * cnt / total), "count": cnt}
                for gid, cnt in counter.most_common(8)
            ]
    except Exception as e:
        logger.debug(f"[PROFILE] genre stats (DB column) error: {e}")

    # Fallback — legacy path using TMDB genres weighted by recency
    try:
        _, all_genres = await _infer_genres_from_history_full(db, user, profile)
        total_weight = sum(all_genres.values()) or 1
        return [
            {"id": gid, "percentage": round(100 * w / total_weight), "count": w}
            for gid, w in all_genres.most_common(8)
        ]
    except Exception as e:
        logger.debug(f"[PROFILE] genre stats (TMDB fallback) error: {e}")
        return []


async def compute_longest_session(
    db: AsyncSession, user_filter, excl_filters: list,
) -> int:
    """Longest binge-watch chain in minutes. A 'marathon' is a sequence of
    back-to-back playback sessions where each starts within 30 min of the
    previous one ending. Each session's contribution is capped by its
    media's runtime so a paused/abandoned session doesn't inflate the chain.
    Returns the total watched time (in minutes) of the longest chain."""
    try:
        result = await db.execute(
            select(
                PlaybackSession.started_at,
                PlaybackSession.ended_at,
                PlaybackSession.last_seen_at,
                PlaybackSession.duration_ticks,
            )
            .where(user_filter, *excl_filters)
            .order_by(PlaybackSession.started_at)
        )
        chain_secs = 0
        longest_secs = 0
        chain_end = None
        for row in result.all():
            if not row.started_at:
                continue

            media_secs = int(row.duration_ticks / 10_000_000) if row.duration_ticks else 0
            ended = row.ended_at or row.last_seen_at
            elapsed = int((ended - row.started_at).total_seconds()) if ended and ended >= row.started_at else 0
            # Cap elapsed by media runtime — a paused 139h session must not count
            watched = min(elapsed, media_secs) if media_secs > 0 else elapsed
            if watched <= 0:
                watched = media_secs
            if watched <= 0:
                continue

            if chain_end and (row.started_at - chain_end).total_seconds() <= MARATHON_GAP_SECONDS:
                chain_secs += watched
            else:
                chain_secs = watched
            chain_end = row.started_at + timedelta(seconds=watched)

            if chain_secs > longest_secs:
                longest_secs = chain_secs
        return longest_secs // 60
    except Exception as e:
        logger.debug(f"[PROFILE] longest session error: {e}")
        return 0


async def compute_media_type_ratio(
    db: AsyncSession, user_filter, excl_filters: list,
) -> dict:
    """Total playback time split between movies and series (Episodes).
    Returns counts + minutes for each bucket so the UI can show a ratio
    donut and a 'X movies vs Y episodes' subtitle."""
    result = {"movie_plays": 0, "movie_minutes": 0, "series_plays": 0, "series_minutes": 0}
    try:
        rows = await db.execute(
            select(
                PlaybackSession.item_type,
                PlaybackSession.started_at,
                PlaybackSession.ended_at,
                PlaybackSession.last_seen_at,
                PlaybackSession.duration_ticks,
            ).where(user_filter, *excl_filters)
        )
        for row in rows.all():
            secs = 0
            if row.started_at:
                ended = row.ended_at or row.last_seen_at
                if ended and ended >= row.started_at:
                    secs = int((ended - row.started_at).total_seconds())
            if secs <= 0 and row.duration_ticks:
                secs = int(row.duration_ticks / 10_000_000)

            kind = (row.item_type or "").lower()
            if kind == "movie":
                result["movie_plays"] += 1
                result["movie_minutes"] += secs // 60
            elif kind == "episode":
                result["series_plays"] += 1
                result["series_minutes"] += secs // 60
    except Exception as e:
        logger.debug(f"[PROFILE] media type ratio error: {e}")
    return result


async def compute_hour_buckets(
    db: AsyncSession, user_filter, excl_filters: list,
) -> list[dict]:
    """Plays per time-of-day bucket:
       morning (6-11), afternoon (12-17), evening (18-22), night (23-5).
    Used on the profile card to paint a night-owl / morning-bird profile."""
    buckets = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
    try:
        result = await db.execute(
            select(
                func.extract("hour", PlaybackSession.started_at).label("hr"),
                func.count(PlaybackSession.id).label("cnt"),
            )
            .where(user_filter, *excl_filters)
            .group_by("hr")
        )
        for row in result.all():
            h = int(row.hr)
            if 6 <= h <= 11:
                buckets["morning"] += row.cnt
            elif 12 <= h <= 17:
                buckets["afternoon"] += row.cnt
            elif 18 <= h <= 22:
                buckets["evening"] += row.cnt
            else:
                buckets["night"] += row.cnt
    except Exception as e:
        logger.debug(f"[PROFILE] hour stats error: {e}")
    return [{"bucket": k, "count": v} for k, v in buckets.items()]


async def compute_day_stats(db: AsyncSession, user_filter, excl_filters: list) -> list[dict] | None:
    """Plays per weekday (Mon=0..Sun=6)."""
    try:
        result = await db.execute(
            select(
                func.extract("dow", PlaybackSession.started_at).label("dow"),
                func.count(PlaybackSession.id).label("cnt"),
            )
            .where(user_filter, *excl_filters)
            .group_by("dow")
        )
        dow_map = {int(r.dow): r.cnt for r in result.all()}
        # PostgreSQL: dow 0=Sunday, 1=Monday... Convert to Mon=0..Sun=6
        return [
            {"day": i, "count": dow_map.get((i + 1) % 7, 0)}
            for i in range(7)
        ]
    except Exception as e:
        logger.debug(f"[PROFILE] day stats error: {e}")
        return None
