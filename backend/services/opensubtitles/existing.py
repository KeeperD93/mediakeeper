"""Playback des sous-titres et pistes audio existants (ffprobe + Emby + externes)."""
import asyncio
import json as _json

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from ._constants import logger
from .paths import _resolve_local_path, _empty_existing_payload
from .streams import _extract_first_emby_item, _parse_ffprobe_streams, _parse_emby_media_streams, _scan_external_subtitles


async def get_existing_subtitles(db: AsyncSession, item_id: str) -> dict:
    """Fetch les sous-titres et pistes audio existants via ffprobe (fiable).
    Use Emby uniquement for fetch le path du file."""
    from services.emby import _get_emby_config

    cfg = await _get_emby_config(db)
    if not cfg:
        logger.warning(f"[opensubtitles] existing/{item_id}: Emby not configured")
        return _empty_existing_payload()

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    media_streams = []

    try:
        client = get_internal_client()
        logger.info(f"[opensubtitles] existing/{item_id}: querying Emby")
        res = await client.get(
            f"{url}/Items",
            params={
                "Ids": item_id,
                "Fields": "Path,MediaSources,MediaStreams",
                "Limit": "1",
            },
            headers=headers, timeout=10.0,
        )
        if res.status_code != 200:
            logger.warning(f"[opensubtitles] existing/{item_id}: Emby returned {res.status_code}")
            return _empty_existing_payload()

        item_data = _extract_first_emby_item(res.json())
        if not item_data:
            logger.warning(f"[opensubtitles] existing/{item_id}: item not found in Emby")
            return _empty_existing_payload()
        sources = item_data.get("MediaSources") or []
        file_path = sources[0].get("Path", "") if sources else ""
        media_streams = sources[0].get("MediaStreams", []) if sources else []
        if not file_path:
            file_path = item_data.get("Path") or ""
        if not media_streams:
            media_streams = item_data.get("MediaStreams") or []
        if not file_path:
            logger.warning(f"[opensubtitles] No file path for item {item_id}")
            fallback_streams, fallback_audio = _parse_emby_media_streams(media_streams)
            return {
                "streams": fallback_streams,
                "audio_streams": fallback_audio,
                "file_path": "",
                "analysis_source": "emby",
            }
    except Exception as e:
        logger.error(f"[opensubtitles] existing/{item_id}: exception: {e}")
        return _empty_existing_payload()

    local_path = await _resolve_local_path(db, file_path)
    logger.info(f"[opensubtitles] existing: emby={file_path} local={local_path}")

    if not local_path:
        # The resolver refused the Emby-reported path (outside configured
        # media roots, inside backup zone, or unresolvable). Falling back
        # to ffprobe on "" would launch the subprocess with an empty
        # argument, and _scan_external_subtitles("") would iterate the
        # process CWD for .srt files — neither is acceptable. Use the
        # Emby-reported MediaStreams as the sole source instead.
        fallback_streams, fallback_audio = _parse_emby_media_streams(media_streams)
        return {
            "streams": fallback_streams,
            "audio_streams": fallback_audio,
            "file_path": "",
            "analysis_source": "emby",
        }

    streams = []
    audio_streams = []
    analysis_source = "ffprobe"
    data = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", local_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        if not stdout.strip():
            logger.warning(f"[opensubtitles] ffprobe empty for {local_path}")
            analysis_source = "emby"
        else:
            data = _json.loads(stdout)
            streams, audio_streams = _parse_ffprobe_streams(data)
    except asyncio.TimeoutError:
        logger.error(f"[opensubtitles] ffprobe timeout for {local_path}")
        analysis_source = "emby"
    except Exception as e:
        logger.error(f"[opensubtitles] ffprobe error: {e}")
        analysis_source = "emby"

    media_duration_sec = 0
    if analysis_source == "ffprobe" and data:
        try:
            media_duration_sec = float(data.get("format", {}).get("duration", 0))
        except (ValueError, TypeError):
            pass

    if analysis_source == "emby":
        streams, audio_streams = _parse_emby_media_streams(media_streams)

    streams.extend(_scan_external_subtitles(local_path))

    return {
        "streams": streams,
        "audio_streams": audio_streams,
        "file_path": local_path,
        "media_duration_sec": round(media_duration_sec, 1),
        "analysis_source": analysis_source,
    }
