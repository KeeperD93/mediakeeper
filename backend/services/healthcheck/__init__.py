"""
HealthCheck service — analyze media file health via the Emby API.

Check: obsolete codecs, low resolution, abnormal bitrate, containers
obsolete, large files, missing audio, HDR without fallback.

Package split into modules (Rule 9, <= 300 lines). Legacy imports
`from services.healthcheck import X` continuent de functionner.
"""
from .config import DEFAULT_CONFIG, OBSOLETE_CONTAINERS, OBSOLETE_VIDEO_CODECS
from .results import (
    get_healthcheck_grouped,
    get_healthcheck_issues,
    get_healthcheck_poster_details,
)
from .scan import get_scan_status, run_healthcheck
from .summary import get_healthcheck_summary

__all__ = [
    "DEFAULT_CONFIG",
    "OBSOLETE_CONTAINERS",
    "OBSOLETE_VIDEO_CODECS",
    "get_healthcheck_grouped",
    "get_healthcheck_issues",
    "get_healthcheck_poster_details",
    "get_healthcheck_summary",
    "get_scan_status",
    "run_healthcheck",
]
