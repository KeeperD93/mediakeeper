"""GDPR constants shared between the services."""
from typing import Final

# One settings row per fingerprint of a person erased at their request.
GDPR_ERASED_KEY_PREFIX: Final[str] = "gdpr.erased."
