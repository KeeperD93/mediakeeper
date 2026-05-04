"""Parsing des pistes (ffprobe / Emby) et scan des sous-titres externes."""
from pathlib import Path

from ._constants import _IMAGE_CODECS


def _extract_first_emby_item(payload) -> dict | None:
    """
    Normalize the various Emby/Jellyfin response shapes encountered
    according to les endpoints et versions :
    - {"Items": [...]}
    - {...item unique...}
    - [{...item...}]
    """
    if isinstance(payload, dict):
        items = payload.get("Items")
        if isinstance(items, list):
            return items[0] if items else None
        if any(key in payload for key in ("MediaSources", "MediaStreams", "Path")):
            return payload
        return None
    if isinstance(payload, list):
        return payload[0] if payload else None
    return None


def _parse_ffprobe_streams(data: dict) -> tuple[list[dict], list[dict]]:
    streams = []
    audio_streams = []

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type", "")
        tags = stream.get("tags", {})
        lang_code = tags.get("language", tags.get("LANGUAGE", ""))
        title = tags.get("title", tags.get("TITLE", ""))
        disposition = stream.get("disposition", {})
        is_default = disposition.get("default", 0) == 1
        is_forced = disposition.get("forced", 0) == 1
        codec_name = stream.get("codec_name", "")

        if codec_type == "subtitle":
            streams.append({
                "index": stream.get("index", 0),
                "type": "subtitle",
                "language": lang_code or "?",
                "title": title,
                "codec": codec_name.upper(),
                "is_external": False,
                "is_forced": is_forced,
                "is_default": is_default,
                "is_image_based": codec_name.lower() in _IMAGE_CODECS,
                "path": "",
            })
        elif codec_type == "audio":
            channels = stream.get("channels", 0)
            bitrate = int(stream.get("bit_rate", 0)) // 1000 if stream.get("bit_rate") else 0
            audio_streams.append({
                "index": stream.get("index", 0),
                "type": "audio",
                "language": lang_code or "?",
                "title": title,
                "codec": codec_name.upper(),
                "channels": channels,
                "bitrate": bitrate,
                "is_default": is_default,
            })

    return streams, audio_streams


def _parse_emby_media_streams(media_streams: list[dict]) -> tuple[list[dict], list[dict]]:
    streams = []
    audio_streams = []

    for stream in media_streams:
        stream_type = (stream.get("Type") or "").lower()
        codec_name = (stream.get("Codec") or stream.get("CodecName") or "").strip()
        language = (stream.get("Language") or "").strip() or "?"
        title = stream.get("Title") or stream.get("DisplayTitle") or ""

        if stream_type == "subtitle":
            streams.append({
                "index": stream.get("Index", 0),
                "type": "subtitle",
                "language": language,
                "title": title,
                "codec": codec_name.upper(),
                "is_external": bool(stream.get("IsExternal")),
                "is_forced": bool(stream.get("IsForced")),
                "is_default": bool(stream.get("IsDefault")),
                "is_image_based": codec_name.lower() in _IMAGE_CODECS,
                "path": "",
            })
        elif stream_type == "audio":
            bitrate_value = stream.get("BitRate") or 0
            try:
                bitrate = int(bitrate_value) // 1000 if bitrate_value else 0
            except (TypeError, ValueError):
                bitrate = 0
            audio_streams.append({
                "index": stream.get("Index", 0),
                "type": "audio",
                "language": language,
                "title": title,
                "codec": codec_name.upper(),
                "channels": stream.get("Channels", 0) or 0,
                "bitrate": bitrate,
                "is_default": bool(stream.get("IsDefault")),
            })

    return streams, audio_streams


def _scan_external_subtitles(local_path: str) -> list[dict]:
    streams = []
    media_path = Path(local_path)
    subtitle_exts = {".srt", ".ass", ".ssa", ".sub", ".vtt", ".idx"}

    try:
        for ext_file in media_path.parent.iterdir():
            if ext_file.stem.startswith(media_path.stem) and ext_file.suffix.lower() in subtitle_exts:
                parts = ext_file.stem.replace(media_path.stem, "").strip(".").split(".")
                lang = parts[0] if parts and parts[0] else "?"
                streams.append({
                    "index": -1,
                    "type": "subtitle",
                    "language": lang,
                    "title": ext_file.name,
                    "codec": ext_file.suffix.lstrip(".").upper(),
                    "is_external": True,
                    "is_forced": "forced" in ext_file.stem.lower(),
                    "is_default": False,
                    "is_image_based": False,
                    "path": str(ext_file),
                })
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass

    return streams
