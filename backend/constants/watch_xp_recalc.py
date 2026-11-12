"""Codes of the watch XP recalculation, read by its summary and the admin card."""
from typing import Final

# Why a watched title pays no watch XP.
SKIP_BEFORE_LEDGER: Final[str] = "before_ledger"
SKIP_ERASED: Final[str] = "erased"
SKIP_EXCLUDED: Final[str] = "excluded"
SKIP_PARALLEL: Final[str] = "parallel"
SKIP_NO_ACCOUNT: Final[str] = "no_account"
SKIP_NOT_EARNING: Final[str] = "not_earning"
SKIP_COOLDOWN: Final[str] = "cooldown"

# Why a player loses all their watch XP: no statistics left (deleted or merged into
# another user), no title watched to the end, or none of their watched titles pays.
LOST_NO_STATS: Final[str] = "no_stats"
LOST_NO_END: Final[str] = "no_end"
LOST_NOT_DUE: Final[str] = "not_due"
