"""Display status of a trophy in the portal achievement payloads.

Mirrors ``TROPHY_STATUS`` in ``frontend/src/constants/achievements.ts`` — keep
the values in sync.
"""
from typing import Final

__all__ = [
    "TROPHY_STATUS_LOCKED",
    "TROPHY_STATUS_PROGRESS",
    "TROPHY_STATUS_SECRET",
    "TROPHY_STATUS_UNLOCKED",
]

TROPHY_STATUS_UNLOCKED: Final[str] = "unlocked"
TROPHY_STATUS_PROGRESS: Final[str] = "progress"
TROPHY_STATUS_LOCKED: Final[str] = "locked"
#: An unearned secret, whatever its progress: shown by name and icon only.
TROPHY_STATUS_SECRET: Final[str] = "secret"
