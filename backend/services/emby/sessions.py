"""Active Emby/Jellyfin sessions (cache + dashboard summary)."""
import asyncio
import time
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client

from .config import _get_emby_config

logger = logging.getLogger("mediakeeper.emby")


# ── Cache sessions raw (TTL 5s) — avoid 6-8 calls Emby/min ────────────────
_raw_sessions_cache: list | None = None
_raw_sessions_cache_ts: float = 0
_sessions_lock = asyncio.Lock()
_SESSIONS_TTL = 5  # secondes


def _reset_sessions_cache() -> None:
    global _raw_sessions_cache, _raw_sessions_cache_ts
    _raw_sessions_cache = None
    _raw_sessions_cache_ts = 0


async def get_raw_sessions(db: AsyncSession) -> list:
    """Fetch les sessions Emby/Jellyfin raw with un cache shared."""
    global _raw_sessions_cache, _raw_sessions_cache_ts
    now = time.monotonic()
    if _raw_sessions_cache is not None and (now - _raw_sessions_cache_ts) < _SESSIONS_TTL:
        return _raw_sessions_cache

    async with _sessions_lock:
        now = time.monotonic()
        if _raw_sessions_cache is not None and (now - _raw_sessions_cache_ts) < _SESSIONS_TTL:
            return _raw_sessions_cache

        cfg = await _get_emby_config(db)
        if not cfg:
            return []

        url, api_key = cfg
        headers = {"X-Emby-Token": api_key}

        try:
            client = get_internal_client()
            res = await client.get(f"{url}/Sessions", headers=headers)
            if res.status_code != 200:
                logger.warning(f"get_raw_sessions: Emby HTTP {res.status_code}")
                return _raw_sessions_cache or []
            sessions = res.json()
            _raw_sessions_cache = sessions
            _raw_sessions_cache_ts = time.monotonic()
            return sessions
        except Exception as e:
            logger.error(f"Error get_raw_sessions: {e}")
            return _raw_sessions_cache or []


async def get_sessions(db: AsyncSession):
    """Fetch les sessions actives sur Emby/Jellyfin for le dashboard."""
    sessions = await get_raw_sessions(db)

    result = []
    for s in sessions:
        if not s.get("UserName"):
            continue

        now_playing = s.get("NowPlayingItem")
        play_state = s.get("PlayState", {})

        thumb_id = ""
        if now_playing:
            if now_playing.get("Type") == "Episode":
                thumb_id = now_playing.get("SeriesId", "")
            elif now_playing.get("Type") == "Audio":
                thumb_id = now_playing.get("AlbumId", "") or now_playing.get("Id", "")
            else:
                thumb_id = now_playing.get("Id", "")

        position = play_state.get("PositionTicks", 0)
        duration = now_playing.get("RunTimeTicks", 0) if now_playing else 0
        progress = round((position / duration) * 100, 1) if duration > 0 else 0

        # Skip sessions where playback is finished (progress >= 98%)
        if progress >= 98:
            continue

        result.append({
            "user": s.get("UserName", "Inconnu"),
            "user_id": s.get("UserId", ""),
            "device": s.get("DeviceName", "Inconnu"),
            "client": s.get("Client", "Inconnu"),
            "ip": s.get("RemoteEndPoint", ""),
            "is_playing": now_playing is not None and not play_state.get("IsPaused", False),
            "is_paused": play_state.get("IsPaused", False),
            "media": now_playing.get("Name", "") if now_playing else "",
            "media_type": now_playing.get("Type", "") if now_playing else "",
            "series": now_playing.get("SeriesName", "") if now_playing else "",
            "episode": (
                f"S{now_playing.get('ParentIndexNumber', 0):02d}E{now_playing.get('IndexNumber', 0):02d}"
                if now_playing and now_playing.get("Type") == "Episode" else ""
            ),
            "item_id": now_playing.get("Id", "") if now_playing else "",
            "session_id": s.get("Id", ""),
            "thumb_url": f"/api/emby/image/{thumb_id}" if thumb_id else "",
            "progress": progress,
        })

    return result


async def get_streams_count(db: AsyncSession) -> int:
    """Return le number de playbacks en cours."""
    try:
        sessions = await get_raw_sessions(db)
        return sum(
            1
            for session in sessions
            if session.get("NowPlayingItem") and not session.get("PlayState", {}).get("IsPaused", False)
        )
    except Exception:
        return 0
