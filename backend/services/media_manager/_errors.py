"""Stable error codes for hard runtime failures in media-manager services.

Soft validation outcomes (``path_not_allowed``, ``source_not_found``,
``destination_not_a_directory``, etc.) are returned as 200 OK + body so
the frontend can surface them as user feedback. The codes listed below
signal a hard runtime failure caught by the service layer (filesystem
error, permission race, unexpected exception) and trigger a 500
HTTPException in the route handler.

The route handler imports :data:`HARD_FAIL_CODES` and maps any error
code listed here to ``raise HTTPException(status_code=500, detail=code)
from None`` — the same service-layer-catch pattern used by
``rename.py``, empirically recognised by CodeQL as a barrier guard for
``py/stack-trace-exposure``.
"""
from __future__ import annotations

HARD_FAIL_CODES: frozenset[str] = frozenset({
    "move_failed",
    "move_overwrite_failed",
    "delete_failed",
    "create_folder_failed",
    "create_folders_failed",
    "check_conflicts_failed",
})
