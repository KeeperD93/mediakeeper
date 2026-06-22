"""Notification ``type`` slugs written by the portal producers and read by the
bell + the Discord templates.

Centralised so producers don't hand-write the strings; the Discord lookup
tables in :mod:`services.discord` key off these same string values.
"""
from typing import Final

__all__ = [
    "NOTIF_EVENT_INVITATION",
    "NOTIF_EVENT_ACCEPTED",
    "NOTIF_EVENT_DECLINED",
    "NOTIF_EVENT_MODIFIED",
    "NOTIF_EVENT_CANCELLED",
    "NOTIF_EVENT_REMOVED",
    "NOTIF_REQUEST_APPROVED",
    "NOTIF_REQUEST_AVAILABLE",
    "NOTIF_TICKET_REPLIED",
    "NOTIF_TICKET_RESOLVED",
]

NOTIF_EVENT_INVITATION: Final[str] = "event_invitation"
NOTIF_EVENT_ACCEPTED: Final[str] = "event_accepted"
NOTIF_EVENT_DECLINED: Final[str] = "event_declined"
NOTIF_EVENT_MODIFIED: Final[str] = "event_modified"
NOTIF_EVENT_CANCELLED: Final[str] = "event_cancelled"
NOTIF_EVENT_REMOVED: Final[str] = "event_removed"
NOTIF_REQUEST_APPROVED: Final[str] = "request_approved"
NOTIF_REQUEST_AVAILABLE: Final[str] = "request_available"
NOTIF_TICKET_REPLIED: Final[str] = "ticket_replied"
NOTIF_TICKET_RESOLVED: Final[str] = "ticket_resolved"
