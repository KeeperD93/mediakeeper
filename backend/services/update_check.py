"""Update check: is a newer MediaKeeper release published on GitHub?

One anonymous GET to the public GitHub releases API, cached in memory for six
hours: nothing about the instance is sent. Off when the admin setting is off
or, with priority, when ``MK_DISABLE_UPDATE_CHECK`` is truthy.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from constants import env_vars
from core.env_flags import env_truthy
from core.http_client import get_external_client
from services.settings import get_setting, set_setting

logger = logging.getLogger("mediakeeper.update_check")

UPDATE_CHECK_SETTING_KEY = "system.update_check_enabled"
_RELEASES_API_URL = "https://api.github.com/repos/KeeperD93/mediakeeper/releases"
_RELEASE_PAGE_URL = "https://github.com/KeeperD93/mediakeeper/releases/tag/{tag}"
_CACHE_TTL_SECONDS = 6 * 3600
# Enough history to find the newest stable release behind a run of pre-releases.
_RELEASES_PER_PAGE = 20

# Pre-release stages in ascending order; a stable release outranks them all.
_STAGE_RANK = {"beta": 0, "rc": 1}
_STABLE_RANK = len(_STAGE_RANK)
_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?:-(beta|rc)\.(\d+))?")

_release_cache: dict[str, object] = {"tags": None, "at": None}


def _version_key(version: str) -> tuple[int, int, int, int, int] | None:
    """Sortable ``(major, minor, patch, stage rank, stage number)`` key for
    ``X.Y.Z`` / ``X.Y.Z-rc.N`` / ``X.Y.Z-beta.N`` (optional ``v``), else None."""
    m = _VERSION_RE.fullmatch(version)
    if not m:
        return None
    major, minor, patch, stage, number = m.groups()
    if stage is None:
        return int(major), int(minor), int(patch), _STABLE_RANK, 0
    return int(major), int(minor), int(patch), _STAGE_RANK[stage], int(number)


def _is_stable(key: tuple[int, int, int, int, int]) -> bool:
    return key[3] == _STABLE_RANK


def _newest_release(tags: list[str], current_version: str) -> str | None:
    """Newest tag strictly above ``current_version``, or None.

    A stable install only follows stable releases; a pre-release install also
    follows newer pre-releases, so testers hear about the next one.
    """
    current = _version_key(current_version)
    if current is None:
        return None
    candidates = [
        (key, tag)
        for tag in tags
        if (key := _version_key(tag)) is not None
        and key > current
        and (_is_stable(key) or not _is_stable(current))
    ]
    return max(candidates)[1] if candidates else None


async def _published_tags() -> list[str]:
    """Release tags listed by GitHub, cached for six hours (failures included,
    so an unreachable GitHub is not retried on every page load)."""
    now = datetime.now(timezone.utc)
    cached_at = _release_cache["at"]
    if cached_at is not None and (now - cached_at).total_seconds() < _CACHE_TTL_SECONDS:
        return _release_cache["tags"]
    tags: list[str] = []
    try:
        resp = await get_external_client().get(
            _RELEASES_API_URL,
            params={"per_page": _RELEASES_PER_PAGE},
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        tags = [
            release["tag_name"]
            for release in resp.json()
            if isinstance(release, dict)
            and not release.get("draft")
            and isinstance(release.get("tag_name"), str)
        ]
    except (httpx.HTTPError, OSError, ValueError, TypeError) as exc:
        # ValueError also covers malformed JSON and the SSRF guard's UnsafeOutboundURL.
        logger.warning("[UPDATE_CHECK] release lookup failed: %s", exc)
    _release_cache.update({"tags": tags, "at": now})
    return tags


async def is_update_check_enabled(db: AsyncSession) -> bool:
    """Admin switch, on by default: only an explicit "false" turns it off."""
    return await get_setting(db, UPDATE_CHECK_SETTING_KEY) != "false"


async def set_update_check_enabled(db: AsyncSession, enabled: bool) -> None:
    await set_setting(db, UPDATE_CHECK_SETTING_KEY, "true" if enabled else "false")


async def get_update_status(db: AsyncSession, current_version: str) -> dict:
    """Update-check payload for the admin UI. No outbound call when disabled."""
    locked = env_truthy(env_vars.MK_DISABLE_UPDATE_CHECK)
    enabled = not locked and await is_update_check_enabled(db)
    latest = _newest_release(await _published_tags(), current_version) if enabled else None
    return {
        "enabled": enabled,
        "locked": locked,
        "current_version": current_version,
        "latest_version": latest.removeprefix("v") if latest else None,
        "update_available": latest is not None,
        # Built from a tag that matched _VERSION_RE, never from API-supplied URLs.
        "release_url": _RELEASE_PAGE_URL.format(tag=latest) if latest else None,
    }
