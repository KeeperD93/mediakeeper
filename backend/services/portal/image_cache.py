"""On-disk image proxy + cache for TMDB posters / backdrops.

When the admin enables ``network.image_cache_enabled``, every poster
URL the API hands to the frontend is rewritten to flow through this
service. The first request for a given URL downloads the bytes from
the TMDB CDN and saves them under ``/data/cache/images/<sha256>.<ext>``;
subsequent requests stream the file straight from disk.

Why this matters:
- Reduces outbound bandwidth from the NAS (TMDB only pays once per
  unique image instead of once per page load).
- Keeps the portal responsive when TMDB rate-limits or has a slow
  CDN edge.
- The user explicitly opted out of a size cap — purge is manual via
  a scheduler task (and a clear button in the admin UI later).

Flag freshness:
- ``_enabled`` is a module-level snapshot, refreshed at startup and
  at the start of any endpoint that hands TMDB items to the frontend
  (via :func:`refresh_enabled_flag`). The TTL means an admin toggle
  propagates within ~30 s without any cross-process IPC.
- ``_normalize`` reads the snapshot synchronously (no ``await``
  available where TMDB results are reshaped).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
import urllib.parse
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from constants.portal_paths import IMAGE_PROXY_PATH
from core.http_client import get_external_client
from core.url_safety import ALLOWED_IMAGE_HOST, UnsafeOutboundURL, is_allowed_image_url
from services.settings import get_setting

logger = logging.getLogger("mediakeeper.portal.image_cache")

CACHE_DIR = Path(os.environ.get("MK_IMAGE_CACHE_DIR", "/data/cache/images"))
SETTING_KEY = "network.image_cache_enabled"

# Single source of truth for the suffixes TMDB actually serves. Drives
# both the cache filename allowlist (severs the user → path taint flow
# at the suffix boundary) and the cached-byte content-type lookup.
_SUFFIX_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
_ALLOWED_SUFFIXES = frozenset(_SUFFIX_TO_MIME)

# How long a cached ``_enabled`` snapshot stays trusted before we
# re-read the DB. 30 s feels right for admin toggles: long enough
# that high-traffic endpoints don't query the settings table on
# every call, short enough that the admin notices the change.
_ENABLED_TTL_SECONDS = 30.0

_enabled = False
_enabled_last_refresh = 0.0

_stats: dict[str, int] = {"hits": 0, "misses": 0}


async def refresh_enabled_flag(db: AsyncSession, *, force: bool = False) -> bool:
    """Re-read the toggle from settings if the cached snapshot is stale.

    Returns the current value. Callers that hand TMDB items to the
    frontend should invoke this near the top of their request handler
    so a freshly-toggled admin preference propagates quickly.
    """
    global _enabled, _enabled_last_refresh
    now = time.time()
    if not force and (now - _enabled_last_refresh) < _ENABLED_TTL_SECONDS:
        return _enabled
    try:
        raw = await get_setting(db, SETTING_KEY)
    except Exception as e:  # noqa: BLE001 -- best-effort, log + keep
        logger.warning("image_cache: failed to read %s: %s", SETTING_KEY, e)
        return _enabled
    _enabled = (raw or "").strip().lower() == "true"
    _enabled_last_refresh = now
    return _enabled


def is_enabled() -> bool:
    """Synchronous flag accessor for code paths that can't ``await``.

    Reads the snapshot updated by :func:`refresh_enabled_flag` — when
    the snapshot has never been initialised the function returns
    ``False`` (the conservative default).
    """
    return _enabled


def proxied_url(original_url: str) -> str:
    """Replace a TMDB CDN URL with the local proxy URL.

    Encodes the original URL so the proxy can fetch from the right
    upstream. Non-TMDB URLs are returned unchanged — this keeps
    avatars and other inline images out of the cache scope.

    Uses the same strict hostname check as the proxy endpoint so the
    rewrite decision and the validation stay in lockstep: an URL that
    fails :func:`is_allowed_image_url` is left as-is (and the browser
    will hit the upstream directly, where CORS/CSP still apply).
    """
    if not is_allowed_image_url(original_url):
        return original_url
    encoded = urllib.parse.quote(original_url, safe="")
    return f"{IMAGE_PROXY_PATH}?u={encoded}"


def _hash_for(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _path_for(url: str) -> Path:
    digest = _hash_for(url)
    # Allowlist the suffix against the 5 image types TMDB serves. Any
    # other value (or none) falls back to ``.bin``. This severs the
    # user → path taint flow at its source: the final filename inside
    # CACHE_DIR can never inherit a path separator, a filesystem
    # reserved character or a control byte from the URL, regardless of
    # what slips past the upstream host check. Suffix preservation on
    # legitimate URLs keeps the .jpg / .webp hint visible in DevTools.
    raw_suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    suffix = raw_suffix if raw_suffix in _ALLOWED_SUFFIXES else ".bin"
    # Stay in the os.path string domain that CodeQL py/path-injection
    # explicitly annotates. ``os.path.normpath`` is one of the three
    # recognised normalisers (along with ``abspath`` and ``realpath``)
    # per github/codeql Stdlib.qll, and the ``startswith`` check after
    # it is a documented SafeAccessCheck barrier. Building the candidate
    # through ``os.path.join`` + ``normpath`` rather than through the
    # ``/`` operator means the user-derived components never reach a
    # ``Path()`` constructor until the safety check has cleared them.
    cache_root_norm = os.path.normpath(os.fspath(CACHE_DIR))
    candidate_norm = os.path.normpath(
        os.path.join(cache_root_norm, f"{digest}{suffix}")
    )
    if not candidate_norm.startswith(cache_root_norm + os.sep):
        raise UnsafeOutboundURL("path_outside_cache")
    return Path(candidate_norm)


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_or_serve(original_url: str) -> tuple[bytes, str]:
    """Return ``(bytes, content_type)`` for the requested URL.

    Hits the disk first; on miss, downloads from upstream and saves
    a copy. Errors fall back to a one-shot fetch without persistence
    so the user never sees a broken image just because the disk
    write failed.

    Defence in depth: the public endpoint (:mod:`api.image_proxy`)
    already validates the URL via :func:`is_allowed_image_url`. Here
    we re-validate inline (scheme + hostname compared against
    ``ALLOWED_IMAGE_HOST`` as a literal constant) AND rebuild the
    upstream URL from a hardcoded host so the request sent to httpx
    can only ever target the TMDB CDN. The hostname comparison happens
    at the call site of ``client.get`` so CodeQL's ``py/full-ssrf``
    barrier model recognises the sanitiser.
    """
    parsed = urllib.parse.urlparse(original_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host != ALLOWED_IMAGE_HOST:
        raise UnsafeOutboundURL("image_url_rejected")
    # Rebuild the upstream URL from the literal host. The path / query
    # remain user-influenced but cannot redirect the request to any
    # host other than TMDB.
    upstream = f"https://{ALLOWED_IMAGE_HOST}{parsed.path}"
    if parsed.query:
        upstream = f"{upstream}?{parsed.query}"

    await asyncio.to_thread(_ensure_cache_dir)
    path = _path_for(upstream)
    if path.exists():
        _stats["hits"] += 1
        cached = await asyncio.to_thread(path.read_bytes)
        return cached, _guess_content_type(path)

    _stats["misses"] += 1
    try:
        client = get_external_client()
        resp = await client.get(upstream, timeout=10.0)
        if resp.status_code != 200:
            logger.warning(
                "image_cache: upstream HTTP %s for %s", resp.status_code, upstream
            )
            return resp.content, resp.headers.get("content-type", "image/jpeg")
        content = resp.content
        try:
            await asyncio.to_thread(path.write_bytes, content)
        except OSError as e:
            # Disk full / permissions / read-only mount — return the
            # bytes anyway so the user sees the image; the next request
            # will try the write again.
            logger.warning("image_cache: write failed for %s: %s", path, e)
        return content, resp.headers.get("content-type", "image/jpeg")
    except httpx.HTTPError as e:
        logger.warning("image_cache: upstream fetch failed for %s: %s", upstream, e)
        raise


def _guess_content_type(path: Path) -> str:
    """Crude suffix-to-MIME mapping; good enough for TMDB CDN content."""
    return _SUFFIX_TO_MIME.get(path.suffix.lower(), "application/octet-stream")


def get_cache_stats() -> dict:
    """Snapshot for the admin readout — same shape as the TMDB cache."""
    keys = 0
    value_bytes = 0
    if CACHE_DIR.exists():
        try:
            for entry in CACHE_DIR.iterdir():
                if entry.is_file():
                    keys += 1
                    try:
                        value_bytes += entry.stat().st_size
                    except OSError:  # noqa: S110 -- best-effort stat per entry, skip broken file
                        pass
        except OSError as e:
            logger.warning("image_cache: stat failed on %s: %s", CACHE_DIR, e)
    return {
        "name": "Image cache (TMDB)",
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "keys": keys,
        "max_keys": None,
        "ttl_seconds": None,
        "value_bytes": value_bytes,
    }


def clear_cache() -> int:
    """Drop every cached file + reset the counters.

    Returns the number of files removed. Errors on individual files
    are logged but never raised — partial purge is better than no
    purge when the disk is in trouble.
    """
    removed = 0
    if CACHE_DIR.exists():
        for entry in CACHE_DIR.iterdir():
            if entry.is_file():
                try:
                    entry.unlink()
                    removed += 1
                except OSError as e:
                    logger.warning("image_cache: unlink failed for %s: %s", entry, e)
    _stats["hits"] = 0
    _stats["misses"] = 0
    return removed
