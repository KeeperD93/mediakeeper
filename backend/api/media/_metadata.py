"""/metadata endpoint — ffprobe analysis of video/audio/subtitle tracks."""
import asyncio
import json
import logging
import os

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from models.user import User
from services.media_manager import _validate_path, format_size

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
            logger.error(f"[metadata] ffprobe empty output. stderr: {stderr_out.decode()[:500]}")
            return None, f"ffprobe_empty_output. Stderr: {stderr_out.decode()[:200]}"
        return json.loads(stdout), None
    except asyncio.TimeoutError:
        logger.error(f"[metadata] ffprobe timeout for {path!r}")
        return None, "Timeout ffprobe (> 30s)"
    except json.JSONDecodeError as e:
        logger.error(f"[metadata] JSON parse error: {e}")
        return None, f"ffprobe_json_parse_error: {e}"
    except Exception as e:
        logger.error(f"[metadata] Exception: {e}")
        return None, f"ffprobe_error: {str(e)}"


def _parse_format(fmt: dict) -> dict:
    result = {}
    size_bytes = int(fmt.get("size", 0))
    if size_bytes:
        result["taille"] = format_size(size_bytes)
    duration_s = float(fmt.get("duration", 0))
    if duration_s:
        h = int(duration_s // 3600)
        m = int((duration_s % 3600) // 60)
        s = int(duration_s % 60)
        result["duree"] = f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"
    bitrate = int(fmt.get("bit_rate", 0))
    if bitrate:
        result["debit_global"] = f"{bitrate // 1000} kbps"
    return result


def _parse_streams(streams: list) -> tuple[list, list, list]:
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
            track = {
                "codec": s.get("codec_name", "—").upper(),
                "profil": s.get("profile", ""),
                "resolution": f"{s.get('width', '?')}×{s.get('height', '?')}",
                "fps": s.get("r_frame_rate", "").replace("/1", "") + " fps" if s.get("r_frame_rate") else "",
                "bitrate": f"{int(s['bit_rate']) // 1000} kbps" if s.get("bit_rate") else "",
                "hdr": _detect_hdr(s),
                "titre": title,
            }
            video_tracks.append({k: v for k, v in track.items() if v})

        elif codec_type == "audio":
            channels = s.get("channels", 0)
            ch_label = {1: "Mono", 2: "Stereo", 6: "5.1", 8: "7.1"}.get(channels, f"{channels} ch")
            track = {
                "langue": lang,
                "codec": s.get("codec_name", "—").upper(),
                "canaux": ch_label,
                "bitrate": f"{int(s['bit_rate']) // 1000} kbps" if s.get("bit_rate") else "",
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
    logger.info(f"[metadata] Requested path: {path!r}")

    err = _validate_path(path)
    if err:
        logger.warning(f"[metadata] Path validation failed: {err} for {path!r}")
        return {"error": f"path_not_allowed: {err}"}

    if not os.path.isfile(path):
        logger.warning(f"[metadata] File not found: {path!r}")
        return {"error": "file_not_found"}

    logger.info(f"[metadata] Running ffprobe on: {path!r}")
    data, ffp_err = await _run_ffprobe(path)
    if ffp_err:
        return {"error": ffp_err}

    streams = data.get("streams", [])
    logger.info(f"[metadata] ffprobe OK: {len(streams)} streams")

    result = _parse_format(data.get("format", {}))
    video_tracks, audio_tracks, sub_tracks = _parse_streams(streams)
    result["pistes_video"] = video_tracks
    result["pistes_audio"] = audio_tracks
    result["pistes_sous_titres"] = sub_tracks
    return result
