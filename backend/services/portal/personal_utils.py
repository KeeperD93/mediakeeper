"""Shared helpers for the personal recommendation layer.

Contains constants, the playback SQL filter, temporal weighting, dedup
helpers and the interleave + emby-index lookups used by both the
"Recommended for you" and "Because you watched" flows.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.portal.emby_tmdb_index import EmbyTmdbIndex

logger = logging.getLogger("mediakeeper.portal.personal")

# Catch-all TMDB genre IDs. These match so many items (especially Drama
# = 18) that using them as a signal gives useless recommendations. They
# are excluded from the "top genres" ranking but kept as a fallback when
# the history has *only* catch-all signals so the row is never empty.
CATCH_ALL_GENRES = {18}  # 18 = Drama

# Temporal weighting applied when inferring genres from playback history.
# Recent plays are stronger signals because tastes drift over time.
_WEIGHT_RECENT_DAYS = 7    # < 7 days old  -> weight 3
_WEIGHT_MEDIUM_DAYS = 30   # < 30 days old -> weight 2
# Everything older -> weight 1
_WEIGHT_RECENT = 3
_WEIGHT_MEDIUM = 2
_WEIGHT_OLD = 1

# How many recent plays to sample when deriving genre preferences.
_HISTORY_SAMPLE = 30
# How many plays to consider when picking the "latest watched" pivot.
_LATEST_POOL = 1

# Map Emby's `Genres` CSV strings (FR + EN variants) back to TMDB genre IDs
# so the profile page can render icons/colours keyed on canonical IDs.
# The stats aggregate comes from PlaybackSession.genres (full history) —
# unknown names are dropped silently.
TMDB_GENRE_NAME_TO_ID: dict[str, int] = {
    # French
    "Action": 28, "Aventure": 12, "Animation": 16,
    "Comédie": 35, "Comedie": 35,
    "Crime": 80, "Policier": 80,
    "Documentaire": 99, "Drame": 18,
    "Familial": 10751, "Famille": 10751,
    "Fantastique": 14, "Fantasy": 14,
    "Histoire": 36, "Horreur": 27,
    "Musique": 10402,
    "Mystère": 9648, "Mystere": 9648,
    "Romance": 10749,
    "Science-Fiction": 878, "Science Fiction": 878,
    "Téléfilm": 10770, "Telefilm": 10770,
    "Thriller": 53, "Guerre": 10752, "Western": 37,
    # English (fallback)
    "Adventure": 12, "Comedy": 35, "Documentary": 99,
    "Drama": 18, "Family": 10751, "History": 36,
    "Horror": 27, "Music": 10402, "Mystery": 9648,
    "TV Movie": 10770, "War": 10752,
    # TV-specific
    "Action & Adventure": 10759, "Sci-Fi & Fantasy": 10765,
    "War & Politics": 10768, "Kids": 10762, "News": 10763,
    "Reality": 10764, "Soap": 10766, "Talk": 10767,
}


def _playback_user_filter(user: User, profile: UserProfile):
    """
    Build the WHERE filter that maps a Portal profile to its rows in
    ``PlaybackSession``. We match on BOTH ``user.username`` (the Emby
    login, stable) and ``profile.display_name`` (the Portal nickname,
    user-editable) to cover:
    - fresh users where both strings are still equal;
    - users who renamed their Portal profile after having history;
    - edge cases where the stats collector stored the Emby "Name" field
      which may differ from the login in unusual Emby setups.
    """
    names: list[str] = []
    if user and user.username:
        names.append(user.username)
    if profile and profile.display_name and profile.display_name not in names:
        names.append(profile.display_name)
    if not names:
        # Poison value so the caller still gets a valid SQL clause that
        # returns zero rows instead of crashing.
        return PlaybackSession.user_name == "__no_user__"
    return PlaybackSession.user_name.in_(names)


def _weight_for_age(now: datetime, started_at: Optional[datetime]) -> int:
    """Temporal weight for a playback based on its age."""
    if started_at is None:
        return _WEIGHT_OLD
    # Normalise naive datetimes to UTC so the delta is consistent. Emby
    # sessions are stored with tzinfo, but a DB driver edge case could
    # strip it — be forgiving.
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    age = now - started_at
    if age < timedelta(days=_WEIGHT_RECENT_DAYS):
        return _WEIGHT_RECENT
    if age < timedelta(days=_WEIGHT_MEDIUM_DAYS):
        return _WEIGHT_MEDIUM
    return _WEIGHT_OLD


def _coerce_int(value) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _interleave(a: list[dict], b: list[dict], max_n: int = 20) -> list[dict]:
    """
    Interleave two lists alternating entries from each, up to ``max_n``
    items total. When one list is exhausted, the remainder of the other
    list fills the rest. Used to mix movies and TV shows in the
    "Recommended for you" row without concatenating one after the other.
    """
    out: list[dict] = []
    i = j = 0
    while len(out) < max_n and (i < len(a) or j < len(b)):
        if i < len(a):
            out.append(a[i])
            i += 1
            if len(out) >= max_n:
                break
        if j < len(b):
            out.append(b[j])
            j += 1
    return out


async def _get_indexed_tmdb_ids(
    db: AsyncSession, media_type: str,
) -> set[int]:
    """
    Return the set of TMDB ids already present in the Emby library for
    ``media_type`` ("movie" or "tv"). Used to filter out "already seen" items
    from recommendation rows so the user is shown genuinely new stuff.
    """
    stmt = select(EmbyTmdbIndex.tmdb_id).where(
        EmbyTmdbIndex.media_type == media_type,
    )
    try:
        res = await db.execute(stmt)
        return {int(x) for x in res.scalars().all() if x is not None}
    except Exception as e:
        logger.debug("[PERSONAL] indexed tmdb ids fetch failed (%s): %s", media_type, e)
        return set()


async def _count_total_plays(
    db: AsyncSession, user: User, profile: UserProfile,
) -> int:
    """Total playback sessions for the user."""
    try:
        result = await db.execute(
            select(func.count(PlaybackSession.id))
            .where(_playback_user_filter(user, profile))
        )
        return result.scalar() or 0
    except Exception as e:
        logger.debug("[PERSONAL] total plays count failed: %s", e)
        return 0
