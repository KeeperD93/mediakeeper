"""Login-security marker, block timings and the security dashboard API's error
codes, shared by the sign-in and password-change routes, the rate-limit keys, the
CSP report log and the dashboard."""
from typing import Final

__all__ = [
    "UNKNOWN_CLIENT_IP",
    "FAIL_WINDOW_SECONDS",
    "TEMP_BLOCK_SECONDS",
    "SELF_BLOCK_FORBIDDEN",
    "INVALID_SCOPE",
    "BLOCK_REQUIRES_IP_OR_USERNAME",
    "INVALID_IP",
]

#: Stands in for a client IP that cannot be read: stored and matched like an
#: address by the sign-in and password-change routes, and a single shared
#: rate-limit bucket.
UNKNOWN_CLIENT_IP: Final[str] = "unknown"

#: How long a failed attempt counts, and how long the automatic block it can set lasts.
FAIL_WINDOW_SECONDS: Final[int] = 300
TEMP_BLOCK_SECONDS: Final[int] = 600

#: Error codes of the security dashboard API (manual blocks, attempts filter).
SELF_BLOCK_FORBIDDEN: Final[str] = "self_block_forbidden"
INVALID_SCOPE: Final[str] = "invalid_scope"
BLOCK_REQUIRES_IP_OR_USERNAME: Final[str] = "block_requires_ip_or_username"
INVALID_IP: Final[str] = "invalid_ip"
