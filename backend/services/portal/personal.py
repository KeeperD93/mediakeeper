"""
Personal recommendation facade — public API for the "Recommended for you"
and "Because you watched" rows.

Implementation is split across four modules to keep each file under 300 lines:

  - personal_utils.py   — shared helpers (playback filter, temporal weighting,
                           interleave, indexed-ids lookup, total plays count).
  - personal_genres.py  — genre inference from playback history (with and
                           without full counter for premium stats).
  - personal_recos.py   — get_recommendations_for_user + get_recommendations_premium.
  - personal_watched.py — get_because_you_watched + series index resolver.

Consumers import from this file, not the split modules, so the public API
stays stable.
"""
from services.portal.personal_utils import (
    _playback_user_filter,
    _weight_for_age,
    _coerce_int,
    _interleave,
    _get_indexed_tmdb_ids,
    _count_total_plays,
    CATCH_ALL_GENRES,
)
from services.portal.personal_genres import (
    _infer_genres_from_history,
    _infer_genres_from_history_full,
)
from services.portal.personal_recos import (
    get_recommendations_for_user,
    get_recommendations_premium,
)
from services.portal.personal_watched import get_because_you_watched

__all__ = [
    # Public API
    "get_recommendations_for_user",
    "get_recommendations_premium",
    "get_because_you_watched",
    # Helpers re-exported for profile_stats / api layers
    "_playback_user_filter",
    "_weight_for_age",
    "_coerce_int",
    "_interleave",
    "_get_indexed_tmdb_ids",
    "_count_total_plays",
    "_infer_genres_from_history",
    "_infer_genres_from_history_full",
    "CATCH_ALL_GENRES",
]
