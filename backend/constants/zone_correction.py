"""Error codes of the tool that takes back the trophies the UTC clock gave wrongly."""
from typing import Final

ZONE_NOT_CHOSEN: Final[str] = "zone_not_chosen"
ZONE_SAVED_AT_UNKNOWN: Final[str] = "zone_saved_at_unknown"
PLAN_CHANGED: Final[str] = "plan_changed"
ALREADY_RUNNING: Final[str] = "already_running"
BACKUP_INCOMPLETE: Final[str] = "backup_incomplete"
