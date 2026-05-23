"""Centralised env var names consumed by ``core.app_startup``.

Routing the env var names through this module — instead of inline
string literals at each ``os.getenv`` callsite — lets static analysis
(CodeQL ``py/clear-text-logging-sensitive-data``) avoid misclassifying
the lookup result as sensitive data via keyword-spotting on names like
``TRUSTED_PROXIES`` (``TRUSTED`` is matched as a credential keyword by
the upstream classifier).

Scope is intentionally limited to env vars actually read by
``backend/core/app_startup.py``. A wider centralisation across the
whole backend is tracked separately in the bug-tracker as a tech-debt
cycle.
"""
from typing import Final

MK_PROCESS_ROLE: Final[str] = "MK_PROCESS_ROLE"
MK_DEBUG: Final[str] = "MK_DEBUG"
MK_DB_SCHEMA_MODE: Final[str] = "MK_DB_SCHEMA_MODE"
TRUSTED_PROXIES: Final[str] = "TRUSTED_PROXIES"
FRONTEND_ORIGIN: Final[str] = "FRONTEND_ORIGIN"
COOKIE_SECURE: Final[str] = "COOKIE_SECURE"
