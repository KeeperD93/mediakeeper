"""
XP (Experience Points) service for the Portal gamification system.

Split by responsibility: ``_levels`` (level curve), ``_grants`` (who earns,
the ledger and direct grants), ``_watch`` (watch XP).
"""
from ._grants import (
    ACHIEVEMENT_XP_ACTION as ACHIEVEMENT_XP_ACTION,
    ACTIVITY_XP_ACTIONS as ACTIVITY_XP_ACTIONS,
    DAILY_REQUEST_XP_CAP as DAILY_REQUEST_XP_CAP,
    EARNING_ACCOUNT as EARNING_ACCOUNT,
    XP_TABLE as XP_TABLE,
    account_earns as account_earns,
    achievement_xp_reference as achievement_xp_reference,
    grant_daily_login_xp as grant_daily_login_xp,
    grant_xp as grant_xp,
)
from ._levels import (
    MAX_LEVEL as MAX_LEVEL,
    MIN_LEVEL as MIN_LEVEL,
    level_floor_xp as level_floor_xp,
    level_from_xp as level_from_xp,
    xp_for_level as xp_for_level,
)
from ._watch import (
    MIN_WATCH_PERCENT as MIN_WATCH_PERCENT,
    WATCH_XP_ITEM_TYPES as WATCH_XP_ITEM_TYPES,
    grant_watch_xp as grant_watch_xp,
)

__all__ = [
    "ACHIEVEMENT_XP_ACTION",
    "ACTIVITY_XP_ACTIONS",
    "DAILY_REQUEST_XP_CAP",
    "EARNING_ACCOUNT",
    "MAX_LEVEL",
    "MIN_LEVEL",
    "MIN_WATCH_PERCENT",
    "WATCH_XP_ITEM_TYPES",
    "XP_TABLE",
    "account_earns",
    "achievement_xp_reference",
    "grant_daily_login_xp",
    "grant_watch_xp",
    "grant_xp",
    "level_floor_xp",
    "level_from_xp",
    "xp_for_level",
]
