"""Shared definitions of what counts as watching.

Single source for the collector, the watch-time aggregates (admin and
profile) and the trophy checks, so they can never disagree on it.
"""

# Emby / Jellyfin positions and runtimes are counted in 100 ns ticks.
TICKS_PER_SECOND = 10_000_000

# Watch time and watched titles are a video notion: music and other media keep
# their per-title time but never count as the user's watching.
WATCH_ITEM_TYPES = frozenset({"Movie", "Episode"})

# Keys of a play's ``watched_by_hour``: the UTC hour its seconds were watched in.
WATCH_HOUR_KEY_FORMAT = "%Y-%m-%dT%H"

# History imported from another statistics tool keeps these session key prefixes;
# the collector never writes them.
IMPORTED_SESSION_KEY_PREFIXES = ("js_", "jsplugin_")
