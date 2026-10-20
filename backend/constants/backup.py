"""Backup naming limit shared by the API schema and the archive writer."""
from typing import Final

# Longest label kept in a backup file name: the listing's file name check
# (services/backup/listing.py) accepts exactly this many characters.
BACKUP_LABEL_MAX_LENGTH: Final[int] = 40
