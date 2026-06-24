"""TMDB media-type slugs shared by the TMDB service and its route handlers.

Centralising the ``movie`` / ``tv`` literals so the search/detail endpoints,
the per-type key mapping and the path-param validation cannot drift apart.
"""
from typing import Final

__all__ = [
    "TMDB_MEDIA_MOVIE",
    "TMDB_MEDIA_TV",
    "TMDB_MEDIA_TYPES",
]

#: TMDB movie segment (endpoint path + ``media_type`` discriminator).
TMDB_MEDIA_MOVIE: Final[str] = "movie"

#: TMDB series segment (endpoint path + ``media_type`` discriminator).
TMDB_MEDIA_TV: Final[str] = "tv"

#: The two media types the app proxies from TMDB; used to validate an
#: incoming ``media_type`` before building an endpoint URL.
TMDB_MEDIA_TYPES: Final[frozenset[str]] = frozenset({TMDB_MEDIA_MOVIE, TMDB_MEDIA_TV})
