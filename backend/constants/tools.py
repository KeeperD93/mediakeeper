"""Tool-registry identifiers shared by the settings layer and its consumers.

Centralising the ``emby`` / ``tmdb`` / ``opensubtitles`` slugs so the
``TOOLS_DEFINITION`` registry and the per-tool lookups (settings save, ping,
onboarding status) cannot drift apart on a rename or a typo.

Scope note: these are the *tool registry* keys only. The ``UserProfile``
account-source flag (also ``"emby"``) is a different concept, centralised as
``SOURCE_EMBY`` in ``services.portal.admin_users_constants``; the active
media-source discriminator (``"emby"`` / ``"jellyfin"``) is yet another.
"""
from typing import Final

__all__ = [
    "TOOL_EMBY",
    "TOOL_TMDB",
    "TOOL_OPENSUBTITLES",
]

#: Emby media-source tool id (``TOOLS_DEFINITION`` key + settings namespace).
TOOL_EMBY: Final[str] = "emby"

#: TMDB metadata API tool id.
TOOL_TMDB: Final[str] = "tmdb"

#: OpenSubtitles API tool id.
TOOL_OPENSUBTITLES: Final[str] = "opensubtitles"
