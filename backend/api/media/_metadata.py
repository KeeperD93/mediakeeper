"""/metadata endpoint — ffprobe analysis of video/audio/subtitle tracks."""
import asyncio
import json
import logging
from collections.abc import Callable

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from models.user import User
from services.media_manager import _ensure_within_media_roots, format_size

logger = logging.getLogger("mediakeeper.api.media")
router = APIRouter()


LANG_MAP = {
    "fre": "French", "fra": "French", "fr": "French",
    "eng": "English", "en": "English",
    "jpn": "Japanese", "ja": "Japanese",
    "ger": "German", "deu": "German", "de": "German",
    "spa": "Spanish", "es": "Spanish",
    "ita": "Italian", "it": "Italian",
    "por": "Portuguese", "pt": "Portuguese",
    "chi": "Chinese", "zho": "Chinese", "zh": "Chinese",
    "kor": "Korean", "ko": "Korean",
    "ara": "Arabic", "ar": "Arabic",
    "rus": "Russian", "ru": "Russian",
    "dut": "Dutch", "nld": "Dutch", "nl": "Dutch",
    "dan": "Danish", "da": "Danish",
    "fin": "Finnish", "fi": "Finnish",
    "nor": "Norwegian", "no": "Norwegian",
    "swe": "Swedish", "sv": "Swedish",
    "pol": "Polish", "pl": "Polish",
    "tur": "Turkish", "tr": "Turkish",
    "ces": "Czech", "cze": "Czech", "cs": "Czech",
    "ron": "Romanian", "rum": "Romanian", "ro": "Romanian",
    "hun": "Hungarian", "hu": "Hungarian",
    "ell": "Greek", "gre": "Greek", "el": "Greek",
    "heb": "Hebrew", "he": "Hebrew",
    "tha": "Thai", "th": "Thai",
    "vie": "Vietnamese", "vi": "Vietnamese",
    "ind": "Indonesian", "id": "Indonesian",
    "ukr": "Ukrainian", "uk": "Ukrainian",
    "hin": "Hindi", "hi": "Hindi",
    "und": "Undefined",
}


def _detect_hdr(stream: dict) -> str:
    """Detect the HDR type from the video track metadata."""
    color_transfer = stream.get("color_transfer", "")
    side_data = stream.get("side_data_list", [])
    for sd in side_data:
        sd_type = sd.get("side_data_type", "").lower()
        if "dolby vision" in sd_type:
            return "Dolby Vision"
        if "hdr10+" in sd_type or "hdr10 plus" in sd_type:
            return "HDR10+"
        if "content light" in sd_type or "mastering display" in sd_type:
            return "HDR10"
    if "smpte2084" in color_transfer or "pq" in color_transfer:
        return "HDR10"
    if "arib-std-b67" in color_transfer or "hlg" in color_transfer:
        return "HLG"
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
    """Extract size, duration and bitrate from the ffprobe ``format`` block."""
    result = {}
    size_bytes = _coerce_number(fmt.get("size"), int, "size")
    if size_bytes:
        result["taille"] = format_size(size_bytes)
    duration_s = _coerce_number(fmt.get("duration"), float, "duration")
    if duration_s:
        h = int(duration_s // 3600)
        m = int((duration_s % 3600) // 60)
        s = int(duration_s % 60)
        result["duree"] = f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"
    bitrate = _coerce_number(fmt.get("bit_rate"), int, "bit_rate")
    if bitrate:
        result["debit_global"] = f"{bitrate // 1000} kbps"
    return result


def _parse_streams(streams: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Split ffprobe streams into (video, audio, subtitle) track lists."""
    video_tracks, audio_tracks, sub_tracks = [], [], []

    for s in streams:
        codec_type = s.get("codec_type", "")
        tags = s.get("tags", {})
        lang_code = tags.get("language", tags.get("LANGUAGE", ""))
        lang = LANG_MAP.get(lang_code.lower(), lang_code.upper() if lang_code else "—")
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
                "profil": s.get("profile", ""),
                "resolution": f"{s.get('width', '?')}×{s.get('height', '?')}",
                "fps": s.get("r_frame_rate", "").replace("/1", "") + " fps" if s.get("r_frame_rate") else "",
                "bitrate": f"{v_bitrate // 1000} kbps" if v_bitrate else "",
                "hdr": _detect_hdr(s),
                "titre": title,
            }
            video_tracks.append({k: v for k, v in track.items() if v})

        elif codec_type == "audio":
            channels = s.get("channels", 0)
            ch_label = {1: "Mono", 2: "Stereo", 6: "5.1", 8: "7.1"}.get(channels, f"{channels} ch")
            a_bitrate = _coerce_number(s.get("bit_rate"), int, "bit_rate")
            track = {
                "langue": lang,
                "codec": s.get("codec_name", "—").upper(),
                "canaux": ch_label,
                "bitrate": f"{a_bitrate // 1000} kbps" if a_bitrate else "",
                "titre": title,
                "par_defaut": "Yes" if is_default else "",
                "commentaire": "Yes" if is_commentary else "",
            }
            audio_tracks.append({k: v for k, v in track.items() if v})

        elif codec_type == "subtitle":
            track = {
                "langue": lang,
                "codec": s.get("codec_name", "—").upper(),
                "titre": title,
                "force": "Yes" if is_forced else "",
                "malentendants": "Yes" if is_hearing_impaired else "",
                "par_defaut": "Yes" if is_default else "",
            }
            sub_tracks.append({k: v for k, v in track.items() if v})

    return video_tracks, audio_tracks, sub_tracks


@router.get("/metadata")
async def get_file_metadata(path: str, _: User = Depends(get_current_user)):
    """Analyze a media file with ffprobe — video, audio, subtitles."""
    logger.info("[metadata] Requested path: %r", path)

    # _ensure_within_media_roots applies the os.path.commonpath barrier guard
    # (CodeQL-recognised for py/path-injection) and returns the sanitised Path.
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
    result["pistes_video"] = video_tracks
    result["pistes_audio"] = audio_tracks
    result["pistes_sous_titres"] = sub_tracks
    return result
