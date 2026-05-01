"""
Moteur de notifications Mediakeeper.
Package split into modules (Rule 9, <= 300 lines).

- added_media.py : detection ajouts Emby + file queue + grouping anti-spam
- system.py      : notifications system (offline, duplicate, demande, incident, alerte)
"""
from .added_media import check_and_send_notifications
from .system import send_system_notification

__all__ = [
    "check_and_send_notifications",
    "send_system_notification",
]
