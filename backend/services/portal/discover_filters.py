"""Static category filters for the discover categories layer.

`CATEGORY_FILTERS` is the single source of truth mapping UX category
keys to TMDB query parameters. Separated to keep discover_categories.py
under 300 lines.
"""

LANGUAGE_TO_REGION: dict[str, str] = {
    "fr": "FR", "en": "US", "ja": "JP", "de": "DE", "es": "ES",
    "it": "IT", "pt": "BR", "ko": "KR", "zh": "CN", "nl": "NL",
    "ru": "RU", "sv": "SE", "da": "DK", "no": "NO", "fi": "FI",
    "pl": "PL", "ar": "SA", "tr": "TR", "hi": "IN", "th": "TH",
}

# Placeholders resolved at query time:
#   "TODAY"        -> today's ISO date
#   "CURRENT_YEAR" -> current year (int)
CATEGORY_FILTERS = {
    # ---- Base catalogue browsers (raw Discover endpoints) ----
    "movies":          {"media_type": "movie"},
    "series":          {"media_type": "tv"},
    "documentaries":   {"media_type": "mixed", "with_genres": "99"},
    "anime":           {"media_type": "tv", "with_genres": "16",
                        "with_original_language": "ja"},
    "shows":           {"media_type": "tv", "with_genres": "10764"},  # Reality

    # ---- Clickable Home rows (paginated "see more" destinations) ----
    "popular-movies":  {"media_type": "movie", "default_sort": "popularity"},
    "popular-tv":      {"media_type": "tv",    "default_sort": "popularity"},
    "recommended":     {"media_type": "mixed", "default_sort": "popularity"},
    "upcoming":        {"media_type": "movie", "default_sort": "release_asc",
                        "primary_release_date_gte": "TODAY",
                        "vote_count_gte": "0"},
    "top-rated-year":  {"media_type": "mixed", "default_sort": "rating",
                        "primary_release_year": "CURRENT_YEAR",
                        "first_air_date_year": "CURRENT_YEAR",
                        "vote_count_gte": "100"},
    "oscars":          {"media_type": "movie", "default_sort": "rating",
                        "vote_count_gte": "1500", "vote_average_gte": "7.5"},
    "family":          {"media_type": "mixed", "default_sort": "popularity",
                        "with_genres": "10751"},
    "animation":       {"media_type": "tv", "default_sort": "popularity",
                        "with_genres": "16"},

    # ---- "Categorys par genres" (12 entries) ----
    # Movies and TV have separate genre id namespaces on TMDB, so when a
    # genre has a different id per side we map them via movie_genres /
    # tv_genres. Horror and Thriller stay movie-only (no direct TV equivalent).
    "genre-action":          {"media_type": "mixed", "default_sort": "popularity",
                              "movie_genres": "28",   "tv_genres": "10759"},
    "genre-comedie":         {"media_type": "mixed", "default_sort": "popularity",
                              "with_genres": "35"},
    "genre-aventure":        {"media_type": "mixed", "default_sort": "popularity",
                              "movie_genres": "12",   "tv_genres": "10759"},
    "genre-fantastique":     {"media_type": "mixed", "default_sort": "popularity",
                              "movie_genres": "14",   "tv_genres": "10765"},
    "genre-science-fiction": {"media_type": "mixed", "default_sort": "popularity",
                              "movie_genres": "878",  "tv_genres": "10765"},
    "genre-familial":        {"media_type": "mixed", "default_sort": "popularity",
                              "with_genres": "10751"},
    "genre-drame":           {"media_type": "mixed", "default_sort": "popularity",
                              "with_genres": "18"},
    "genre-animation":       {"media_type": "mixed", "default_sort": "popularity",
                              "with_genres": "16"},
    "genre-horreur":         {"media_type": "movie", "default_sort": "popularity",
                              "with_genres": "27"},
    "genre-thriller":        {"media_type": "movie", "default_sort": "popularity",
                              "with_genres": "53"},
    "genre-mystere":         {"media_type": "mixed", "default_sort": "popularity",
                              "with_genres": "9648"},
    "genre-documentaire":    {"media_type": "mixed", "default_sort": "popularity",
                              "with_genres": "99"},
}

VALID_SORTS = {
    "popularity":   "popularity.desc",
    "release":      None,     # mapped per media_type below
    "release_asc":  None,     # same, ascending (for Upcoming row)
    "rating":       "vote_average.desc",
}


def _resolve_placeholder(value: str) -> str:
    """Resolve `TODAY` / `CURRENT_YEAR` placeholders used in CATEGORY_FILTERS."""
    if value == "TODAY":
        from datetime import date
        return date.today().isoformat()
    if value == "CURRENT_YEAR":
        from datetime import date
        return str(date.today().year)
    return value
