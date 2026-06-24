"""Stable error codes for hard runtime failures in media-manager services.

Soft validation outcomes (``path_not_allowed``, ``source_not_found``,
``destination_not_a_directory``, …) are returned as 200 OK + body so the
frontend can surface them as user feedback. The codes below signal a hard
runtime failure (filesystem error, permission race, unexpected exception);
the move/delete route handler maps any of them to a 500 HTTPException via
``_raise_if_hard_fail`` — the service-layer-catch pattern CodeQL recognises
as a barrier guard for ``py/stack-trace-exposure``.
"""
from __future__ import annotations

from typing import Final

__all__ = ["HARD_FAIL_CODES"]

HARD_FAIL_CODES: Final[frozenset[str]] = frozenset({
    "move_failed",
    "move_overwrite_failed",
    "delete_failed",
    "create_folder_failed",
    "create_folders_failed",
    "check_conflicts_failed",
})
