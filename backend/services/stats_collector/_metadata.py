"""Static description of a playback, read once from an Emby session."""


def _stream(media_streams: list, kind: str) -> dict:
    return next((ms for ms in media_streams if ms.get("Type") == kind), {})


def _resolution(height: int) -> str | None:
    if height >= 2100:
        return "4K"
    if height >= 1000:
        return "1080p"
    if height >= 700:
        return "720p"
    return "SD" if height > 0 else None


def play_method(session: dict) -> str:
    play_state = session.get("PlayState", {})
    if session.get("TranscodingInfo", {}):
        return "Transcode"
    if play_state.get("PlayMethod") == "DirectStream":
        return "DirectStream"
    return play_state.get("PlayMethod") or "DirectPlay"


def genres(now_playing: dict) -> str | None:
    names = now_playing.get("Genres") or now_playing.get("GenreItems") or []
    if names and isinstance(names[0], dict):
        names = [g.get("Name", "") for g in names]
    return ",".join(g for g in names if g) or None


def session_metadata(session: dict) -> dict:
    """Columns of a new ``PlaybackSession`` that describe what is played and how."""
    now_playing = session.get("NowPlayingItem") or {}
    media_streams = now_playing.get("MediaStreams", [])
    video = _stream(media_streams, "Video")
    audio = _stream(media_streams, "Audio")
    subtitle = next(
        (ms for ms in media_streams if ms.get("Type") == "Subtitle" and ms.get("IsExternal", False) is False),
        None,
    ) or next((ms for ms in media_streams if ms.get("Type") == "Subtitle"), None)
    return {
        "user_name": session.get("UserName", ""),
        "item_name": now_playing.get("Name", ""),
        "item_type": now_playing.get("Type", ""),
        "series_name": now_playing.get("SeriesName"),
        "season_number": now_playing.get("ParentIndexNumber"),
        "episode_number": now_playing.get("IndexNumber"),
        "client_name": session.get("Client", ""),
        "device_name": session.get("DeviceName", ""),
        "ip_address": session.get("RemoteEndPoint", ""),
        "play_method": play_method(session),
        "container": now_playing.get("Container", ""),
        "video_codec": video.get("Codec", "").upper() or None,
        "audio_codec": audio.get("Codec", "").upper() or None,
        "resolution": _resolution(video.get("Height", 0)),
        "bitrate": now_playing.get("Bitrate") or video.get("BitRate"),
        "audio_language": audio.get("Language") or audio.get("DisplayLanguage") or None,
        "subtitle_language": (
            subtitle.get("Language") or subtitle.get("DisplayLanguage") if subtitle else None
        ),
        "genres": genres(now_playing),
        "duration_ticks": now_playing.get("RunTimeTicks", 0),
    }
