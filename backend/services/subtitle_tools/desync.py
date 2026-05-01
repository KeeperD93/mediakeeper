"""Detect desync between an SRT and a media's duration."""
import logging
import re
from pathlib import Path

from services.path_config import validate_path_in_roots

from ._parse import _SRT_TS_RE, _SUBTITLE_FILE_EXTENSIONS, _ts_to_seconds, parse_srt_metadata

logger = logging.getLogger("mediakeeper.subtitle_tools")


def check_desync(
    srt_path: str,
    media_duration_sec: float,
    threshold_sec: float = 30.0,
    allow_any_path: bool = False,
) -> dict:
    """Compare the SRT duration with the media duration.

    Return:
        desynced: True if the gap exceeds the threshold
        delta_sec: gap in seconds (positive = SRT is longer)
        srt_duration_sec: position of the last SRT timestamp
        media_duration_sec: media duration
    """
    try:
        if allow_any_path:
            target = Path(srt_path).expanduser().resolve(strict=False)
        else:
            target, path_error = validate_path_in_roots(
                srt_path,
                allow_missing=False,
                must_be_dir=False,
                allowed_suffixes=_SUBTITLE_FILE_EXTENSIONS,
                label="Subtitle file",
            )
            if path_error:
                return {
                    "desynced": False,
                    "delta_sec": 0,
                    "srt_duration_sec": 0,
                    "media_duration_sec": round(media_duration_sec, 1),
                    "error": path_error,
                }

        content = target.read_bytes()
        meta = parse_srt_metadata(content)

        # last_ts is the absolute position, not the relative duration -> recompute.
        all_matches = list(re.finditer(_SRT_TS_RE, content.decode(meta["encoding"], errors="replace")))
        srt_end = _ts_to_seconds(all_matches[-1]) if all_matches else 0

        delta = srt_end - media_duration_sec

        return {
            "desynced": abs(delta) > threshold_sec,
            "delta_sec": round(delta, 1),
            "srt_duration_sec": round(srt_end, 1),
            "media_duration_sec": round(media_duration_sec, 1),
        }

    except Exception as e:
        logger.warning(f"[subtitle_tools] Desync check error: {e}")
        return {
            "desynced": False,
            "delta_sec": 0,
            "srt_duration_sec": 0,
            "media_duration_sec": round(media_duration_sec, 1),
        }
