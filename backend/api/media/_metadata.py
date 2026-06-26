"""/metadata endpoint — ffprobe analysis of video/audio/subtitle tracks.

The response uses machine codes (snake_case EN keys, ISO language codes,
raw byte/second/bps numbers, booleans, HDR slugs). The frontend formats
and localizes them per viewer (i18n) — see MMFileMetaModal.vue.
"""
import asyncio
import json
import logging
from collections.abc import Callable

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from models.user import User
from services.media_manager import _ensure_within_media_roots

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


# ffprobe language tags (ISO 639-2/B, 639-2/T and 639-1) normalised to a
# single canonical code the frontend localizes via mediaManager.languages.*.
LANG_CODE = {
    "fre": "fr", "fra": "fr", "fr": "fr",
    "eng": "en", "en": "en",
    "jpn": "ja", "ja": "ja",
    "ger": "de", "deu": "de", "de": "de",
    "spa": "es", "es": "es",
    "ita": "it", "it": "it",
    "por": "pt", "pt": "pt",
    "chi": "zh", "zho": "zh", "zh": "zh",
    "kor": "ko", "ko": "ko",
    "ara": "ar", "ar": "ar",
    "rus": "ru", "ru": "ru",
    "dut": "nl", "nld": "nl", "nl": "nl",
    "dan": "da", "da": "da",
    "fin": "fi", "fi": "fi",
    "nor": "no", "no": "no",
    "swe": "sv", "sv": "sv",
    "pol": "pl", "pl": "pl",
    "tur": "tr", "tr": "tr",
    "ces": "cs", "cze": "cs", "cs": "cs",
    "ron": "ro", "rum": "ro", "ro": "ro",
    "hun": "hu", "hu": "hu",
    "ell": "el", "gre": "el", "el": "el",
    "heb": "he", "he": "he",
    "tha": "th", "th": "th",
    "vie": "vi", "vi": "vi",
    "ind": "id", "id": "id",
    "ukr": "uk", "uk": "uk",
    "hin": "hi", "hi": "hi",
    "und": "und",
}


def _format_fps(rate: str) -> str:
    """Format an ffprobe ``r_frame_rate`` ("num/den") as "<value> fps".

    Evaluates the fraction so fractional NTSC rates like 24000/1001 render
    as ~23.976 instead of being mangled by a naive ``/1`` string strip
    (24000/1001 -> "24000001"). Whole rates drop their decimals.
    """
    if not rate or "/" not in rate:
        return ""
    num, den = rate.split("/", 1)
    try:
        fps = int(num) / int(den)
    except (ValueError, ZeroDivisionError):
        return ""
    text = f"{fps:.3f}".rstrip("0").rstrip(".") if fps % 1 else str(int(fps))
    return f"{text} fps"


def _detect_hdr(stream: dict) -> str:
    """Detect the HDR type from the video track metadata. Returns a slug
    (``dolby_vision`` / ``hdr10_plus`` / ``hdr10`` / ``hlg``) or ``""``.
    """
    color_transfer = stream.get("color_transfer", "")
    side_data = stream.get("side_data_list", [])
    for sd in side_data:
        sd_type = sd.get("side_data_type", "").lower()
        if "dolby vision" in sd_type:
            return "dolby_vision"
        if "hdr10+" in sd_type or "hdr10 plus" in sd_type:
            return "hdr10_plus"
        if "content light" in sd_type or "mastering display" in sd_type:
            return "hdr10"
    if "smpte2084" in color_transfer or "pq" in color_transfer:
        return "hdr10"
    if "arib-std-b67" in color_transfer or "hlg" in color_transfer:
        return "hlg"
    return ""


async def _run_ffprobe(path: str) -> tuple[dict | None, str | None]:
    """Run ffprobe and return (data, error). data is None on error."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr_out = await asyncio.wait_for(proc.communicate(), timeout=30)
        if not stdout.strip():
            logger.error("[metadata] ffprobe empty output. stderr: %s", stderr_out.decode()[:500])
            return None, "ffprobe_empty_output"
        return json.loads(stdout), None
    except asyncio.TimeoutError:
        logger.error("[metadata] ffprobe timeout for %r", path)
        return None, "ffprobe_timeout"
    except json.JSONDecodeError:
        logger.exception("[metadata] JSON parse error")
        return None, "ffprobe_json_parse_failed"
    except Exception:
        logger.exception("[metadata] ffprobe failed")
        return None, "ffprobe_failed"


def _coerce_number(raw: object, cast: Callable[[object], int | float], field: str) -> int | float:
    """Parse an ffprobe numeric field, tolerating the non-numeric strings
    (e.g. "N/A") ffprobe emits for corrupted files — a raw ``int()`` /
    ``float()`` would raise and turn the whole request into a 500.
    """
    try:
        return cast(raw)
    except (TypeError, ValueError):
        if raw not in (None, ""):
            logger.warning("[metadata] non-numeric %s=%r, using fallback", field, raw)
        return cast(0)


def _parse_format(fmt: dict) -> dict:
    """Extract raw size / duration / bitrate from the ffprobe ``format`` block."""
    result = {}
    size_bytes = _coerce_number(fmt.get("size"), int, "size")
    if size_bytes:
        result["size_bytes"] = size_bytes
    duration_s = _coerce_number(fmt.get("duration"), float, "duration")
    if duration_s:
        result["duration_seconds"] = duration_s
    bitrate = _coerce_number(fmt.get("bit_rate"), int, "bit_rate")
    if bitrate:
        result["overall_bitrate_bps"] = bitrate
    return result


def _parse_streams(streams: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Split ffprobe streams into (video, audio, subtitle) track lists."""
    video_tracks, audio_tracks, sub_tracks = [], [], []

    for s in streams:
        codec_type = s.get("codec_type", "")
        tags = s.get("tags", {})
        raw_lang = tags.get("language", tags.get("LANGUAGE", "")).lower()
        language_code = LANG_CODE.get(raw_lang, raw_lang) if raw_lang else ""
        title = tags.get("title", tags.get("TITLE", ""))
        disposition = s.get("disposition", {})
        is_default = disposition.get("default", 0) == 1
        is_forced = disposition.get("forced", 0) == 1
        is_hearing_impaired = disposition.get("hearing_impaired", 0) == 1
        is_commentary = disposition.get("comment", 0) == 1

        if codec_type == "video":
            v_bitrate = _coerce_number(s.get("bit_rate"), int, "bit_rate")
            track = {
                "codec": s.get("codec_name", "—").upper(),
                "profile": s.get("profile", ""),
                "resolution": f"{s.get('width', '?')}×{s.get('height', '?')}",
                "fps": _format_fps(s.get("r_frame_rate", "")),
                "bitrate_bps": v_bitrate,
                "hdr_type": _detect_hdr(s),
                "title": title,
            }
            video_tracks.append({k: v for k, v in track.items() if v})

        elif codec_type == "audio":
            a_bitrate = _coerce_number(s.get("bit_rate"), int, "bit_rate")
            track = {
                "language_code": language_code,
                "codec": s.get("codec_name", "—").upper(),
                "channels": s.get("channels", 0),
                "bitrate_bps": a_bitrate,
                "title": title,
                "is_default": is_default,
                "is_commentary": is_commentary,
            }
            audio_tracks.append({k: v for k, v in track.items() if v})

        elif codec_type == "subtitle":
            track = {
                "language_code": language_code,
                "codec": s.get("codec_name", "—").upper(),
                "title": title,
                "is_forced": is_forced,
                "is_hearing_impaired": is_hearing_impaired,
                "is_default": is_default,
            }
            sub_tracks.append({k: v for k, v in track.items() if v})

    return video_tracks, audio_tracks, sub_tracks


@router.get("/metadata")
async def get_file_metadata(path: str, _: User = Depends(get_current_user)):
    """Analyze a media file with ffprobe — video, audio, subtitles."""
    logger.info("[metadata] Requested path: %r", path)

    # _ensure_within_media_roots applies the os.path.realpath + prefix barrier
    # guard (CodeQL-recognised for py/path-injection) and returns the sanitised Path.
    # Downstream sinks (is_file, ffprobe subprocess) MUST consume this Path.
    resolved = _ensure_within_media_roots(path)
    if resolved is None:
        logger.warning("[metadata] Path validation failed for %r", path)
        return {"error": "path_not_allowed"}

    resolved_str = str(resolved)
    if not resolved.is_file():
        logger.warning("[metadata] File not found: %r", resolved_str)
        return {"error": "file_not_found"}

    logger.info("[metadata] Running ffprobe on: %r", resolved_str)
    data, ffp_err = await _run_ffprobe(resolved_str)
    if ffp_err:
        return {"error": ffp_err}

    streams = data.get("streams", [])
    logger.info("[metadata] ffprobe OK: %d streams", len(streams))

    result = _parse_format(data.get("format", {}))
    video_tracks, audio_tracks, sub_tracks = _parse_streams(streams)
    result["video_tracks"] = video_tracks
    result["audio_tracks"] = audio_tracks
    result["subtitle_tracks"] = sub_tracks
    return result
