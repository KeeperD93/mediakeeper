"""Backup constants shared between the API and the services."""
from typing import Final

# Longest label kept in a backup file name: the listing's file name check
# (services/backup/listing.py) accepts exactly this many characters.
BACKUP_LABEL_MAX_LENGTH: Final[int] = 40

# Refusal code of a restore whose secrets this installation's key cannot read.
BACKUP_KEY_MISMATCH: Final[str] = "backup_key_mismatch"
