"""Build and maintain the Emby ↔ TMDB index (package split, Rule 9 <= 300 lines).

Matching strategy (in priority order, like Jellyseerr / Ombi sync mode):

    1. ``ProviderIds.Tmdb`` — cheapest, exact, trust it.
    2. ``ProviderIds.Imdb`` → TMDB ``/find/{imdb_id}?external_source=imdb_id``
       — deterministic, no false positive.
    3. Fuzzy TMDB search by normalised title + year, only accepted when
       the first hit is a very close match — catches the long tail of
       Emby items whose metadata provider was neither TheMovieDb nor IMDB.
"""
from ._index_ops import _upsert_index, get_emby_item_by_tmdb, is_available_on_emby
from ._match import _coerce_int, _normalise_title, _resolve_by_imdb, _resolve_by_search
from ._sync import sync_emby_tmdb_index

__all__ = [
    "sync_emby_tmdb_index",
    "is_available_on_emby",
    "get_emby_item_by_tmdb",
    "_upsert_index",
    "_coerce_int",
    "_normalise_title",
    "_resolve_by_imdb",
    "_resolve_by_search",
]
