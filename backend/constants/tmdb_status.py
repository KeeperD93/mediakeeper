"""TMDB media status slugs and helper sets consumed by the portal flows."""
from typing import Final

__all__ = [
    "TMDB_STATUS_CANCELED",
    "TMDB_STATUS_ENDED",
    "TMDB_TERMINAL_STATUSES",
]

#: TMDB marks a series as ``ended`` once production finished naturally.
TMDB_STATUS_ENDED: Final[str] = "ended"

#: TMDB marks a series as ``canceled`` when production was cut short.
TMDB_STATUS_CANCELED: Final[str] = "canceled"

#: Statuses that signal no further episode will air; both branches are
#: treated the same way by the availability completeness checker.
TMDB_TERMINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {TMDB_STATUS_ENDED, TMDB_STATUS_CANCELED}
)
