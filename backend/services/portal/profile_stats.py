"""
    Profile page data aggregation for Portal — orchestrator.

Builds the full profile payload in a single call by delegating each
block to a focused module:

  - profile_stats_playback.py — totals, streak, record, rewatched, genres, day stats.
  - profile_stats_history.py  — recent watches, user requests, paginated variants.
  - profile_stats_ranking.py  — monthly XP rank, percentile, movement, top-5 leaderboard.

Public API (re-exported):
  - get_profile_full(db, user, profile) → full dashboard dict
  - get_watch_history_paginated(...)
  - get_my_requests_paginated(...)
  - _compute_streak(...)  — kept for the achievement system (checks_standard).
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from services.portal.personal import _playback_user_filter
from services.portal.exclusions import get_exclusion_filters
from services.portal.profile_stats_playback import (
    compute_totals,
    compute_streak as _compute_streak,
    compute_record_day,
    compute_most_rewatched,
    compute_genre_stats,
    compute_day_stats,
    compute_longest_session,
    compute_media_type_ratio,
    compute_hour_buckets,
    compute_record_month,
)
from services.portal.profile_stats_history import (
    fetch_recent_watches,
    fetch_my_requests,
    get_watch_history_paginated,
    get_my_requests_paginated,
)
from services.portal.profile_stats_ranking import (
    compute_ranking,
    title_for_level,
    tier_for_level,
)
from services.portal.profile_stats_next import fetch_next_to_finish

logger = logging.getLogger("mediakeeper.portal.profile_stats")


async def get_profile_full(
    db: AsyncSession, user: User, profile: UserProfile,
) -> dict:
    """
    Aggregate all data needed by the profile page in a single call:
    playback stats, genre breakdown, recent watches, requests, ranking, title, tier.
    """
    user_filter = _playback_user_filter(user, profile)
    # Load exclusion filters once — same blacklist as the Statistics module
    # (theme songs, intros, test content). Applied to all PlaybackSession queries.
    excl_filters = await get_exclusion_filters(db)

    # Fan out the independent aggregation queries. Each coroutine only
    # reads ``db`` and the two filter tuples, so running them concurrently
    # turns ~13 sequential round-trips (≈400 ms) into ~50 ms on warm caches.
    (
        totals,
        streak,
        record_day,
        rewatched,
        genre_stats,
        day_stats,
        longest_session,
        media_ratio,
        hour_buckets,
        record_month,
        recent_watches,
        my_requests,
        next_to_finish,
        ranking,
    ) = await asyncio.gather(
        compute_totals(db, user_filter, excl_filters),
        _compute_streak(db, user_filter, excl_filters),
        compute_record_day(db, user_filter, excl_filters),
        compute_most_rewatched(db, user_filter, excl_filters),
        compute_genre_stats(db, user, profile, user_filter, excl_filters),
        compute_day_stats(db, user_filter, excl_filters),
        compute_longest_session(db, user_filter, excl_filters),
        compute_media_type_ratio(db, user_filter, excl_filters),
        compute_hour_buckets(db, user_filter, excl_filters),
        compute_record_month(db, user_filter, excl_filters),
        fetch_recent_watches(db, user_filter, excl_filters),
        fetch_my_requests(db, user),
        fetch_next_to_finish(db, user_filter, excl_filters),
        compute_ranking(db, user),
    )
    total_plays, total_minutes = totals
    most_rewatched, most_rewatched_movie, most_rewatched_series = rewatched

    level = profile.level if profile else 1

    return {
        "stats": {
            "total_plays": total_plays,
            "total_minutes": total_minutes,
            "streak": streak,
            "record_day": record_day,
            "most_rewatched": most_rewatched,
            "most_rewatched_movie": most_rewatched_movie,
            "most_rewatched_series": most_rewatched_series,
            "top_genres": genre_stats,
            "day_stats": day_stats,
            "longest_session_minutes": longest_session,
            "media_ratio": media_ratio,
            "hour_buckets": hour_buckets,
            "record_month": record_month,
        },
        "ranking": ranking,
        "title_key": title_for_level(level),
        "rank_tier": tier_for_level(level),
        "recent_watches": recent_watches,
        "my_requests": my_requests,
        "next_to_finish": next_to_finish,
    }


__all__ = [
    "get_profile_full",
    "get_watch_history_paginated",
    "get_my_requests_paginated",
    "_compute_streak",
]
