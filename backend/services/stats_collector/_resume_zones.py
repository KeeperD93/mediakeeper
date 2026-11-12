"""Where Emby saves a resume position, per library.

Emby keeps the saved position at 0 before ``MinResumePct`` of a title, and
never saves one for a title shorter than ``MinResumeDurationSeconds``. Past
``MaxResumePct`` it saves 0 again but marks the title played, which the
collector already reads. Each library has its own values, in its options.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from constants.playback import TICKS_PER_SECOND
from core.http_client import get_internal_client

logger = logging.getLogger("mediakeeper.stats.collector")

_READ_TIMEOUT_SECONDS = 3.0
# Well within the 30 min after which a held row closes: a setting raised in Emby
# releases the rows it held before they lose what they held.
_REFRESH_EVERY = timedelta(minutes=10)


@dataclass(frozen=True)
class ResumeZone:
    min_pct: float
    min_duration_ticks: int

    def start_ticks(self, runtime_ticks: int) -> int | None:
        """First position Emby saves for this title, None when it never saves one."""
        if runtime_ticks <= 0 or runtime_ticks < self.min_duration_ticks:
            return None
        return int(runtime_ticks * self.min_pct / 100)


# Library name -> its zone. A library missing here keeps the caller's defaults.
_zones: dict[str, ResumeZone] = {}
_read_at: datetime | None = None


def resume_zone(library: str | None) -> ResumeZone | None:
    return _zones.get(library) if library else None


def _zone(options: object) -> ResumeZone | None:
    if not isinstance(options, dict):
        return None
    min_pct, min_duration = options.get("MinResumePct"), options.get("MinResumeDurationSeconds")
    if not all(isinstance(value, int | float) and value >= 0 for value in (min_pct, min_duration)):
        return None
    return ResumeZone(min_pct, int(min_duration * TICKS_PER_SECOND))


async def refresh_resume_zones(url: str, api_key: str, now: datetime) -> None:
    """Read every library's resume settings, at most once per ``_REFRESH_EVERY``.

    A failed read keeps what was read before.
    """
    global _read_at
    if _read_at is not None and now - _read_at < _REFRESH_EVERY:
        return
    _read_at = now
    try:
        response = await get_internal_client().get(
            f"{url}/Library/VirtualFolders", headers={"X-Emby-Token": api_key}, timeout=_READ_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        folders = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Library resume settings unavailable: %s", type(exc).__name__)
        return
    if not isinstance(folders, list):
        logger.warning("Library resume settings unavailable: unexpected answer")
        return
    zones = {}
    for folder in folders:
        name = folder.get("Name") if isinstance(folder, dict) else None
        zone = _zone(folder.get("LibraryOptions")) if isinstance(name, str) else None
        if zone is not None:
            zones[name] = zone
    _zones.clear()
    _zones.update(zones)
