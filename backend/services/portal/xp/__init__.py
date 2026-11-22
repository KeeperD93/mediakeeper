"""
XP (Experience Points) service for the Portal gamification system.

Split by responsibility: ``_levels`` (level curve), ``_grants`` (who earns,
the ledger and direct grants), ``_watch`` (watch XP).
"""
from ._grants import ACHIEVEMENT_XP_ACTION as ACHIEVEMENT_XP_ACTION
from ._grants import ACTIVITY_XP_ACTIONS as ACTIVITY_XP_ACTIONS
from ._grants import DAILY_REQUEST_XP_CAP as DAILY_REQUEST_XP_CAP
from ._grants import EARNING_ACCOUNT as EARNING_ACCOUNT
from ._grants import LINKED_ACCOUNT as LINKED_ACCOUNT
from ._grants import XP_TABLE as XP_TABLE
from ._grants import account_earns as account_earns
from ._grants import achievement_xp_reference as achievement_xp_reference
from ._grants import grant_daily_login_xp as grant_daily_login_xp
from ._grants import grant_xp as grant_xp
from ._grants import locked_profile as locked_profile
from ._levels import MAX_LEVEL as MAX_LEVEL
from ._levels import MIN_LEVEL as MIN_LEVEL
from ._levels import level_bar_percent as level_bar_percent
from ._levels import level_floor_xp as level_floor_xp
from ._levels import level_from_xp as level_from_xp
from ._levels import xp_for_level as xp_for_level
from ._watch import COMPLETION_MARK as COMPLETION_MARK
from ._watch import WATCH_XP_ACTIONS as WATCH_XP_ACTIONS
from ._watch import WATCH_XP_COOLDOWN as WATCH_XP_COOLDOWN
from ._watch import WatchedTitle as WatchedTitle
from ._watch import boosted_watch_xp as boosted_watch_xp
from ._watch import completion_reference as completion_reference
from ._watch import grant_completion_xp as grant_completion_xp
from ._watch import watch_action as watch_action
from ._watch import watch_xp_amount as watch_xp_amount
from ._watch import watch_xp_eligible as watch_xp_eligible
