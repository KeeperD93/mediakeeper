"""
OpenSubtitles service — subtitle search and download.

REST API v1: https://opensubtitles.stoplight.io
Auth: API key + login (username/password) → JWT token
Rate limits: 5 downloads/24h (anonymous), 10-1000 (authenticated depending on rank)

Package split into modules (Rule 9, <= 300 lines). Legacy imports
`from services.opensubtitles import X` keep working thanks to the
re-exports below. Submodules remain accessible via
`opensubtitles.auth`, `opensubtitles.search`, etc. (useful for tests
that rely on dependency monkey-patches).
"""
from pathlib import Path  # re-exported (accessed via opensubtitles.Path in tests)

from ._constants import logger, OS_API_BASE, OS_USER_AGENT, _SUBTITLE_FILE_EXTENSIONS
from ._lang import _normalize_lang, _LANG_ALIASES
from .auth import (
    _get_os_config,
    _get_headers,
    _login,
    _token_cache,
    is_configured,
)
from .existing import get_existing_subtitles
from .hashing import compute_file_hash, compute_quality_score
from .library import browse_library, get_emby_libraries
from .matrix import (
    _os_count_cache,
    _OS_COUNT_TTL,
    get_available_counts,
    get_series_matrix,
)
from .paths import (
    _empty_existing_payload,
    _get_local_path_roots,
    _normalize_path_validation_error,
    _resolve_local_path,
    delete_external_subtitle,
    suggest_subtitle_path,
)
from .remove import remove_stream, remove_streams_batch
from .scan import scan_missing_subtitles, search_streams_in_library
from .search import download_subtitle, get_quota, search_subtitles
from .streams import (
    _extract_first_emby_item,
    _parse_emby_media_streams,
    _parse_ffprobe_streams,
    _scan_external_subtitles,
)

# Ensure `get_internal_client` is accessible as a package attribute for
# legacy tests (monkeypatch). Submodules that need it import it directly
# from `core.http_client`.
from core.http_client import get_internal_client, get_external_client

__all__ = [
    "OS_API_BASE",
    "OS_USER_AGENT",
    "browse_library",
    "compute_file_hash",
    "compute_quality_score",
    "delete_external_subtitle",
    "download_subtitle",
    "get_available_counts",
    "get_emby_libraries",
    "get_existing_subtitles",
    "get_quota",
    "get_series_matrix",
    "is_configured",
    "remove_stream",
    "remove_streams_batch",
    "scan_missing_subtitles",
    "search_streams_in_library",
    "search_subtitles",
    "suggest_subtitle_path",
]
