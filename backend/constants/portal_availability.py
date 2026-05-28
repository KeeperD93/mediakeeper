"""Availability status codes shared across the portal availability flow.

Centralising the literals so the route handler and the completeness
checker cannot drift apart — both values flow into the same frontend
cache via ``POST /api/portal/availability``.
"""
from typing import Final

__all__ = [
    "AVAILABILITY_FULL",
    "AVAILABILITY_PARTIAL",
]

#: Series with every aired episode already present in Emby.
AVAILABILITY_FULL: Final[str] = "full"

#: Series with at least one aired episode missing from Emby.
AVAILABILITY_PARTIAL: Final[str] = "partial"
