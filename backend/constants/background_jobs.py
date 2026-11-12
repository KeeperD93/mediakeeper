"""Codes a failed background scan or audit reports in place of its exception text."""
from __future__ import annotations

from typing import Final

SCAN_FAILED: Final[str] = "scan_failed"
AUDIT_FAILED: Final[str] = "audit_failed"
