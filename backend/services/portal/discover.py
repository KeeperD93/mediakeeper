"""
TMDB discover facade — public API for the discover layer.

Implementation is split across three modules to keep each file under 300 lines:

  - discover_lists.py       — simple list endpoints (trending, popular, top-rated,
                              upcoming, family, oscars, by-provider, videos) plus
                              the _normalize / _fetch_list_params helpers.
  - discover_details.py     — get_full_details (cast, crew, videos, reco) and
                              search_tmdb_multi.
  - discover_categories.py  — generic paginated discover (CATEGORY_FILTERS dict,
                              discover_paginated, discover_category, discover_provider).

Consumers import from this file, not the split modules, so the public API
stays stable.
"""
from services.portal.discover_lists import (
    get_trending,
    get_popular_movies,
    get_popular_tv,
    get_top_rated,
    get_top_rated_year,
    get_oscar_winners,
    get_family,
    get_upcoming,
    get_by_provider,
    get_media_videos,
    _fetch_list,
    _fetch_list_params,
    _normalize,
)
from services.portal.discover_details import (
    get_full_details,
    search_tmdb_multi,
)
from services.portal.discover_categories import (
    CATEGORY_FILTERS,
    VALID_SORTS,
    LANGUAGE_TO_REGION,
    discover_paginated,
    discover_category,
    discover_provider,
)

__all__ = [
    # Lists
    "get_trending", "get_popular_movies", "get_popular_tv", "get_top_rated",
    "get_top_rated_year", "get_oscar_winners", "get_family", "get_upcoming",
    "get_by_provider", "get_media_videos", "get_full_details", "search_tmdb_multi",
    # Categories
    "CATEGORY_FILTERS", "VALID_SORTS", "LANGUAGE_TO_REGION",
    "discover_paginated", "discover_category", "discover_provider",
    # Helpers (still accessed by personal.py and the API layer)
    "_fetch_list", "_fetch_list_params", "_normalize",
]
