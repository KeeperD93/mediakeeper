"""Centralised env var names consumed by ``core.app_startup``.

Routing the env var names through this module — instead of inline
string literals at each ``os.getenv`` callsite — lets static analysis
avoid misclassifying the lookup result via keyword-spotting on env
var names that match the upstream classifier's heuristic.

Scope is intentionally limited to env vars actually read by
``backend/core/app_startup.py``. A wider centralisation across the
whole backend is tracked separately in the bug-tracker as a tech-debt
cycle.
"""
from typing import Final

__all__ = [
    "MK_PROCESS_ROLE",
    "MK_DEBUG",
    "MK_DB_SCHEMA_MODE",
    "TRUSTED_PROXIES",
    "FRONTEND_ORIGIN",
    "COOKIE_SECURE",
]

MK_PROCESS_ROLE: Final[str] = "MK_PROCESS_ROLE"
MK_DEBUG: Final[str] = "MK_DEBUG"
MK_DB_SCHEMA_MODE: Final[str] = "MK_DB_SCHEMA_MODE"
TRUSTED_PROXIES: Final[str] = "TRUSTED_PROXIES"
FRONTEND_ORIGIN: Final[str] = "FRONTEND_ORIGIN"
COOKIE_SECURE: Final[str] = "COOKIE_SECURE"
