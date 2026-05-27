"""Enriched sessions (Emby real time) for the Overview page."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.settings import get_active_media_source
from .playback import _load_mk_profile_map, _resolve_user_avatar

logger = logging.getLogger("mediakeeper.stats.aggregator")


async def get_detailed_sessions(db: AsyncSession):
    """
    Return les sessions actives with all les infos de transcode.
    Calls Emby directly for real-time data.
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return []

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return []

    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(f"{url}/Sessions", headers=headers)
        if res.status_code != 200:
            logger.warning(f"get_detailed_sessions: Emby HTTP {res.status_code}")
            return []
        sessions = res.json()
    except Exception as e:
        logger.error(f"Error get_detailed_sessions: {e}")
        return []

    # Batch-resolve MK profiles (avatar + level + tier) keyed by
    # emby_user_id so the Sessions card renders the same photo + tier
    # ring as the leaderboard. Emby-only sessions fall back to the
    # Emby-proxied photo URL + bronze tier via ``_resolve_user_avatar``.
    mk_profiles = await _load_mk_profile_map(
        db, list({s.get("UserId", "") for s in sessions if s.get("UserId")}),
    )

    result = []
    for s in sessions:
        np = s.get("NowPlayingItem")
        if not np or not s.get("UserName"):
            continue
        if (np.get("Type", "").lower() == "theme" or
            np.get("ExtraType", "").lower() == "themesong" or
            np.get("ExtraType", "").lower() == "themevideo"):
            continue

        play_state = s.get("PlayState", {})
        if not (np and (play_state.get("PositionTicks") or not play_state.get("IsPaused", True))):
            if not np:
                continue

        transcode_info = s.get("TranscodingInfo", {})
        media_streams = np.get("MediaStreams", [])
        video_stream = next((ms for ms in media_streams if ms.get("Type") == "Video"), {})
        audio_stream = next((ms for ms in media_streams if ms.get("Type") == "Audio"), {})

        height = video_stream.get("Height", 0)
        width = video_stream.get("Width", 0)

        video_decision = "Direct"
        audio_decision = "Direct"
        if transcode_info:
            if transcode_info.get("IsVideoDirect") is False:
                video_decision = "Transcode"
            if transcode_info.get("IsAudioDirect") is False:
                audio_decision = "Transcode"

        position = play_state.get("PositionTicks", 0)
        duration = np.get("RunTimeTicks", 0)
        progress = round((position / duration) * 100, 1) if duration > 0 else 0

        eta = ""
        remaining_ticks = duration - position
        if remaining_ticks > 0 and (not play_state.get("IsPaused", False)):
            remaining_seconds = remaining_ticks // 10_000_000
            h, remainder = divmod(remaining_seconds, 3600)
            m, secs = divmod(remainder, 60)
            eta = f"{h:02d}:{m:02d}" if h > 0 else f"{m:02d}:{secs:02d}"

        thumb_id = ""
        backdrop_id = np.get("Id", "")
        if np.get("Type") == "Episode":
            thumb_id = np.get("SeriesId", "")
        else:
            thumb_id = np.get("Id", "")

        subtitle_info = next(
            (ms for ms in media_streams if ms.get("Type") == "Subtitle"),
            {}
        )

        def ticks_to_time(t):
            total_sec = t // 10_000_000
            h, remainder = divmod(total_sec, 3600)
            m, secs = divmod(remainder, 60)
            return f"{h}:{m:02d}:{secs:02d}"

        emby_uid = s.get("UserId", "")
        user_meta = _resolve_user_avatar(emby_uid, mk_profiles)

        result.append({
            "user": s.get("UserName", ""),
            "user_id": emby_uid,
            "avatar_url": user_meta["avatar_url"],
            "level": user_meta["level"],
            "tier": user_meta["tier"],
            "device": s.get("DeviceName", ""),
            "client": s.get("Client", ""),
            "client_version": s.get("ApplicationVersion", ""),
            "ip": s.get("RemoteEndPoint", ""),
            "is_playing": not play_state.get("IsPaused", False),
            "is_paused": play_state.get("IsPaused", False),
            "media": np.get("Name", ""),
            "media_type": np.get("Type", ""),
            "series": np.get("SeriesName", ""),
            "episode": (
                f"S{np.get('ParentIndexNumber', 0):02d} - E{np.get('IndexNumber', 0):02d}"
                if np.get("Type") == "Episode" else ""
            ),
            "thumb_url": f"/api/emby/image/{thumb_id}" if thumb_id else "",
            "backdrop_url": f"/api/emby/image/{backdrop_id}?type=Backdrop" if backdrop_id else "",
            "progress": progress,
            "position": ticks_to_time(position),
            "duration": ticks_to_time(duration),
            "eta": eta,
            "container": np.get("Container", ""),
            "transcode_container": transcode_info.get("Container", ""),
            "video_codec": video_stream.get("Codec", "").upper(),
            "video_decision": video_decision,
            "video_height": height,
            "video_width": width,
            "video_bitrate": round((transcode_info.get("Bitrate") or video_stream.get("BitRate") or 0) / 1_000_000, 1),
            "audio_codec": audio_stream.get("Codec", "").upper(),
            "audio_channels": audio_stream.get("Channels", 0),
            "audio_decision": audio_decision,
            "audio_bitrate": round((audio_stream.get("BitRate") or 0) / 1000, 1),
            "audio_language": audio_stream.get("Language", ""),
            "subtitle_language": subtitle_info.get("Language", ""),
            "subtitle_codec": subtitle_info.get("Codec", "").upper(),
        })

    return result
