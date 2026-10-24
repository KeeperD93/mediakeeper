"""Login-security marker and manual-block error codes, shared by the sign-in
routes, the rate-limit keys and the security dashboard API."""
from typing import Final

__all__ = [
    "UNKNOWN_CLIENT_IP",
    "SELF_BLOCK_FORBIDDEN",
    "INVALID_SCOPE",
    "BLOCK_REQUIRES_IP_OR_USERNAME",
]

#: Stands in for a client IP that cannot be read: stored and matched like an
#: address by the sign-in routes, and a single shared rate-limit bucket.
UNKNOWN_CLIENT_IP: Final[str] = "unknown"

#: Error codes of the manual-block API.
SELF_BLOCK_FORBIDDEN: Final[str] = "self_block_forbidden"
INVALID_SCOPE: Final[str] = "invalid_scope"
BLOCK_REQUIRES_IP_OR_USERNAME: Final[str] = "block_requires_ip_or_username"
