"""
Achievement definitions facade — aggregates tiered families, secrets, and constants.

This module is the single public entry point for the achievement data layer.
The definitions themselves are split into three files to keep each under 300 lines:

  - achievement_defs_standard.py  — tiered families (Bronze → Mythique)
  - achievement_defs_secrets.py   — 28 unique secrets (never stacked)
  - achievement_defs_constants.py — SECRET_THEMES, TITLE_REWARDS, TIER_NAMES

Consumers import from this file, not the split files, so the public API stays stable.
"""

from services.portal.achievement_defs_standard import STANDARD_DEFS
from services.portal.achievement_defs_secrets import SECRET_DEFS
from services.portal.achievement_defs_meta import META_DEFS, META_TARGET_CATEGORY
from services.portal.achievement_defs_constants import (
    SECRET_THEMES,
    SECONDARY_CATEGORIES,
    EXCLUSIVE_FROM_META,
    TITLE_REWARDS,
    TIER_NAMES,
)

ACHIEVEMENT_DEFS: list[dict] = STANDARD_DEFS + SECRET_DEFS + META_DEFS

__all__ = [
    "ACHIEVEMENT_DEFS",
    "META_DEFS",
    "META_TARGET_CATEGORY",
    "SECRET_THEMES",
    "SECONDARY_CATEGORIES",
    "EXCLUSIVE_FROM_META",
    "TITLE_REWARDS",
    "TIER_NAMES",
]


def achievements_for_category(category: str) -> list[str]:
    """Return every non-excluded achievement ID that belongs to `category`
    via primary or secondary category (secrets). Meta achievements never
    count toward another meta."""
    ids: list[str] = []
    for d in STANDARD_DEFS + SECRET_DEFS:
        if d["id"] in EXCLUSIVE_FROM_META:
            continue
        if d.get("category") == category:
            ids.append(d["id"])
        elif SECONDARY_CATEGORIES.get(d["id"]) == category:
            ids.append(d["id"])
    return ids
