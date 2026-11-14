"""Verdicts on a display name a member picks, shared by the live check, the profile
update, the first-login wizard and their tests."""
from typing import Final

MIN_LENGTH: Final[int] = 3
# Chinese ideographs and Korean syllables each write a whole syllable.
MIN_LENGTH_SYLLABIC: Final[int] = 2
MAX_LENGTH: Final[int] = 50

INVALID: Final[str] = "invalid"
TOO_SHORT: Final[str] = "too_short"
GENERATED: Final[str] = "generated"
PREVIOUS: Final[str] = "previous"
RESERVED: Final[str] = "reserved"
LOCKED: Final[str] = "locked"
TAKEN: Final[str] = "taken"
CURRENT: Final[str] = "current"
FREE: Final[str] = "free"

ACCEPTED: Final[frozenset[str]] = frozenset({CURRENT, FREE})

# HTTP status of each refusal on a save; the detail sent is ``display_name_<verdict>``.
REFUSAL_STATUS: Final[dict[str, int]] = {
    INVALID: 422,
    TOO_SHORT: 422,
    GENERATED: 409,
    PREVIOUS: 409,
    RESERVED: 409,
    TAKEN: 409,
    LOCKED: 403,
}
