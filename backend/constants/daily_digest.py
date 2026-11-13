"""Limits and item kinds of the portal daily digest, shared by its blocks and their tests."""
from typing import Final

# The account expiry warning shows from this many calendar days before the end.
EXPIRY_WARNING_DAYS: Final[int] = 30
NEWS_LIMIT: Final[int] = 5
FOR_YOU_LIMIT: Final[int] = 5

FOR_YOU_REQUEST_AVAILABLE: Final[str] = "request_available"
FOR_YOU_REQUEST_APPROVED: Final[str] = "request_approved"
FOR_YOU_TICKET_REPLY: Final[str] = "ticket_reply"
