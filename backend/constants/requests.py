"""Media request statuses shared by the request services and the trophy checks,
so a renamed status cannot drift between them."""
from __future__ import annotations

from typing import Final

__all__ = [
    "REQUEST_PENDING",
    "REQUEST_APPROVED",
    "REQUEST_REJECTED",
    "REQUEST_AVAILABLE",
    "OPEN_REQUEST_STATUSES",
    "ACCEPTED_REQUEST_STATUSES",
]

REQUEST_PENDING: Final[str] = "pending"
REQUEST_APPROVED: Final[str] = "approved"
REQUEST_REJECTED: Final[str] = "rejected"
REQUEST_AVAILABLE: Final[str] = "available"

# Requests still waiting for their content.
OPEN_REQUEST_STATUSES: Final[tuple[str, ...]] = (REQUEST_PENDING, REQUEST_APPROVED)

# Requests an admin accepted or that were served: what the Ambassador trophy counts.
ACCEPTED_REQUEST_STATUSES: Final[tuple[str, ...]] = (REQUEST_APPROVED, REQUEST_AVAILABLE)
