"""Image resolution for Discord notifications (TMDB → Imgur → Emby direct)."""
import os
import base64
import logging

from core.http_client import get_internal_client, get_external_client

logger = logging.getLogger("mediakeeper.notifications.discord")


async def _fetch_tmdb_poster(tmdb_id: str | int, tmdb_type: str, db) -> str:
    """Return a public TMDB poster URL (image.tmdb.org CDN) or empty string."""
    if not tmdb_id or tmdb_type not in ("movie", "tv"):
        return ""
    try:
        from services.tmdb import TMDB_BASE, _get_tmdb_key, _tmdb_headers_sync
        api_key = await _get_tmdb_key(db)
        if not api_key:
            return ""
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/{tmdb_type}/{tmdb_id}",
            params={"language": "en-US"},
            headers=_tmdb_headers_sync(api_key),
            timeout=10.0,
        )
        if res.status_code != 200:
            return ""
        poster_path = res.json().get("poster_path")
        if not poster_path:
            return ""
        return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception as e:
        logger.warning(f"[DISCORD] TMDB poster fetch failed: {e}")
        return ""


async def _upload_emby_to_imgur(emby_image_url: str, emby_api_key: str, imgur_client_id: str) -> str:
    """Download from Emby, upload to Imgur, return the Imgur CDN URL."""
    if not imgur_client_id:
        return ""
    try:
        internal_client = get_internal_client()
        img_res = await internal_client.get(
            emby_image_url,
            headers={"X-Emby-Token": emby_api_key},
            timeout=10.0,
        )
        if img_res.status_code != 200:
            return ""
        external_client = get_external_client()
        b64 = base64.b64encode(img_res.content).decode("utf-8")
        imgur_res = await external_client.post(
            "https://api.imgur.com/3/image",
            headers={"Authorization": f"Client-ID {imgur_client_id}"},
            data={"image": b64, "type": "base64"},
            timeout=15.0,
        )
        if imgur_res.status_code == 200:
            return imgur_res.json().get("data", {}).get("link", "")
    except Exception as e:
        logger.warning(f"[DISCORD] Imgur upload failed: {e}")
    return ""


async def _get_image_url(
    item_id: str,
    emby_url: str,
    emby_api_key: str,
    imgur_client_id: str,
    tmdb_id: str | int = "",
    tmdb_type: str = "",
    db=None,
) -> str:
    """Resolve a Discord-reachable image URL.

    Priority: TMDB poster (public CDN) → Imgur upload (proxied from Emby) → empty.
    Emby direct URLs are intentionally not returned — Discord cannot fetch LAN URLs.
    """
    tmdb_url = await _fetch_tmdb_poster(tmdb_id, tmdb_type, db)
    if tmdb_url:
        return tmdb_url

    if not item_id:
        return ""
    client_id = imgur_client_id or os.getenv("IMGUR_CLIENT_ID", "")
    if not client_id:
        return ""
    emby_image_url = f"{emby_url}/Items/{item_id}/Images/Primary"
    return await _upload_emby_to_imgur(emby_image_url, emby_api_key, client_id)
