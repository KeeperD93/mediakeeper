"""Feedback (bug/suggestion) domain slugs and field bounds.

Mirrors the frontend copies in ``frontend/src/constants/feedback.ts`` — keep the
values in sync. The ``feedback_reports`` column widths (migration 061) are the
hard ceiling; every ``MAX_*`` bound below must stay <= its column.
"""
from typing import Final

__all__ = [
    "STATUS_PENDING",
    "STATUS_REJECTED",
    "FEEDBACK_STATUSES",
    "TYPE_BUG",
    "TYPE_SUGGESTION",
    "FEEDBACK_TYPES",
    "PLATFORM_BOTH",
    "PLATFORM_DESKTOP",
    "PLATFORM_MOBILE",
    "FEEDBACK_PLATFORMS",
    "MAX_TITLE",
    "MAX_DESCRIPTION",
    "MAX_REPRODUCTION",
    "MAX_LOCATION",
    "MAX_RESOLUTION",
    "MAX_PSEUDO",
    "MAX_TAGS",
    "MAX_TAG_LEN",
    "RETENTION_DEFAULT_DAYS",
    "RETENTION_MIN_DAYS",
    "RETENTION_MAX_DAYS",
]

#: Moderation-queue states for a stored delegate report.
STATUS_PENDING: Final[str] = "pending"
STATUS_REJECTED: Final[str] = "rejected"
FEEDBACK_STATUSES: Final[frozenset[str]] = frozenset({STATUS_PENDING, STATUS_REJECTED})

#: Report kinds. Anything that is not ``TYPE_SUGGESTION`` is coerced to ``TYPE_BUG``.
TYPE_BUG: Final[str] = "bug"
TYPE_SUGGESTION: Final[str] = "suggestion"
FEEDBACK_TYPES: Final[frozenset[str]] = frozenset({TYPE_BUG, TYPE_SUGGESTION})

#: Target platform. Both boxes ticked (or none) resolves to ``PLATFORM_BOTH``.
PLATFORM_BOTH: Final[str] = "both"
PLATFORM_DESKTOP: Final[str] = "desktop"
PLATFORM_MOBILE: Final[str] = "mobile"
FEEDBACK_PLATFORMS: Final[tuple[str, ...]] = (PLATFORM_BOTH, PLATFORM_DESKTOP, PLATFORM_MOBILE)

# Input field bounds — must stay <= the feedback_reports column widths and mirror
# the frontend maxlength/schema values.
MAX_TITLE: Final[int] = 120
MAX_DESCRIPTION: Final[int] = 1500
MAX_REPRODUCTION: Final[int] = 500
MAX_LOCATION: Final[int] = 120  # zone / module / tab — DB String(120)
MAX_RESOLUTION: Final[int] = 40
MAX_PSEUDO: Final[int] = 100
MAX_TAGS: Final[int] = 12
MAX_TAG_LEN: Final[int] = 30

#: Days a rejected report is kept before the scheduler purges it (admin-tunable).
RETENTION_DEFAULT_DAYS: Final[int] = 30
RETENTION_MIN_DAYS: Final[int] = 1
RETENTION_MAX_DAYS: Final[int] = 365
