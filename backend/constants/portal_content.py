"""Codes the Help Center and News admin routes return for a rejected input."""
from __future__ import annotations

from typing import Final

INVALID_CATEGORY: Final[str] = "invalid_category"
INVALID_LANG: Final[str] = "invalid_lang"
START_AT_MUST_PRECEDE_END_AT: Final[str] = "start_at_must_precede_end_at"
