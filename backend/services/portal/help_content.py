"""Help Center seed — aggregator.

Imports the per-category lists and exposes ``HELP_SEED`` consumed by
``services.portal.help.ensure_seed`` at app boot. Splitting by category
keeps each file under the 300-line file-size cap and makes the
content easier to scan / edit.
"""
from __future__ import annotations

from services.portal.help_content_general import (
    HELP_GENERAL, HELP_ISSUES, HELP_MISC,
)
from services.portal.help_content_profile import HELP_PROFILE
from services.portal.help_content_requests import HELP_REQUESTS


HELP_SEED: list[dict] = [
    *HELP_GENERAL,
    *HELP_REQUESTS,
    *HELP_PROFILE,
    *HELP_ISSUES,
    *HELP_MISC,
]
