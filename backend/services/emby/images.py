"""Proxy images Emby/Jellyfin (posters + avatars) with cache LRU."""
import re
import logging
from collections import OrderedDict

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client

from ._cache import _CACHE_MISS, _get_cached_blob, _store_cached_blob
from .config import _get_emby_config

logger = logging.getLogger("mediakeeper.emby")

_IMAGE_HIT_TTL = 900
_IMAGE_MISS_TTL = 60
_USER_IMAGE_HIT_TTL = 1800
_USER_IMAGE_MISS_TTL = 120
_IMAGE_CACHE_MAX = 256
_USER_IMAGE_CACHE_MAX = 256

_image_cache: "OrderedDict[str, tuple[float, tuple[bytes, str] | None]]" = OrderedDict()
_user_image_cache: "OrderedDict[str, tuple[float, tuple[bytes, str] | None]]" = OrderedDict()


def _reset_image_caches() -> None:
    _image_cache.clear()
    _user_image_cache.clear()


async def proxy_image(db: AsyncSession, item_id: str, image_type: str = "Primary") -> tuple[bytes, str] | None:
    """
    Download an Emby/Jellyfin image on the server side.
    image_type: Primary, Backdrop, Banner, Thumb...
    Return (bytes, content_type) ou None.
    """
    cfg = await _get_emby_config(db)
    if not cfg or not item_id:
        return None

    # Validate item_id: alphanumeric only (anti-SSRF)
    if not re.match(r'^[a-zA-Z0-9]+$', item_id):
        return None

    allowed_types = {"Primary", "Backdrop", "Banner", "Thumb", "Art", "Logo"}
    if image_type not in allowed_types:
        image_type = "Primary"

    cache_key = f"{item_id}:{image_type}"
    cached = _get_cached_blob(_image_cache, cache_key)
    if cached is not _CACHE_MISS:
        return cached

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    max_h = 300 if image_type == "Primary" else 500

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Items/{item_id}/Images/{image_type}",
            params={"maxHeight": max_h},
            headers=headers,
        )
        if res.status_code == 200:
            content_type = res.headers.get("content-type", "image/jpeg")
            return _store_cached_blob(
                _image_cache,
                cache_key,
                (res.content, content_type),
                ttl=_IMAGE_HIT_TTL,
                max_entries=_IMAGE_CACHE_MAX,
            )
        # Fallback to Primary if Backdrop not available
        if image_type != "Primary":
            res = await client.get(
                f"{url}/Items/{item_id}/Images/Primary",
                params={"maxHeight": max_h},
                headers=headers,
            )
            if res.status_code == 200:
                content_type = res.headers.get("content-type", "image/jpeg")
                return _store_cached_blob(
                    _image_cache,
                    cache_key,
                    (res.content, content_type),
                    ttl=_IMAGE_HIT_TTL,
                    max_entries=_IMAGE_CACHE_MAX,
                )
        if res.status_code not in (404,):
            logger.warning(
                "[EMBY] proxy_image HTTP %s pour item_id=%s type=%s",
                res.status_code,
                item_id,
                image_type,
            )
        return _store_cached_blob(
            _image_cache,
            cache_key,
            None,
            ttl=_IMAGE_MISS_TTL,
            max_entries=_IMAGE_CACHE_MAX,
        )
    except Exception as e:
        logger.error("Error proxy_image: %s", e)
        return None


async def proxy_user_image(db: AsyncSession, user_id: str) -> tuple[bytes, str] | None:
    """Download l'image de profil d'un user Emby/Jellyfin."""
    cfg = await _get_emby_config(db)
    if not cfg or not user_id:
        return None

    if not re.match(r'^[a-zA-Z0-9]+$', user_id):
        return None

    cached = _get_cached_blob(_user_image_cache, user_id)
    if cached is not _CACHE_MISS:
        return cached

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Users/{user_id}/Images/Primary",
            params={"maxHeight": 80},
            headers=headers,
        )
        if res.status_code == 200:
            content_type = res.headers.get("content-type", "image/jpeg")
            return _store_cached_blob(
                _user_image_cache,
                user_id,
                (res.content, content_type),
                ttl=_USER_IMAGE_HIT_TTL,
                max_entries=_USER_IMAGE_CACHE_MAX,
            )
        if res.status_code not in (404,):
            logger.warning(
                "[EMBY] proxy_user_image HTTP %s pour user_id=%s",
                res.status_code,
                user_id,
            )
        return _store_cached_blob(
            _user_image_cache,
            user_id,
            None,
            ttl=_USER_IMAGE_MISS_TTL,
            max_entries=_USER_IMAGE_CACHE_MAX,
        )
    except Exception as e:
        logger.error("Error proxy_user_image: %s", e)
        return None
