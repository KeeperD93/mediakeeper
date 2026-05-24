"""Time-shift all timestamps in an SRT file."""
import logging
import re
from pathlib import Path

import chardet

from services.path_config import validate_path_in_roots

from ._parse import _SRT_TS_RE

logger = logging.getLogger("mediakeeper.subtitle_tools")


def shift_srt(filepath: str, offset_ms: int, allow_any_path: bool = False) -> dict:
    """Shift all timestamps in an SRT file by offset_ms milliseconds.

    offset_ms positif = retarder les sous-titres (apparaissent plus tard)
    negative offset_ms = advance subtitles (appear earlier)

    Return: success, path, offset_ms, lines_shifted.
    """
    try:
        if allow_any_path:
            target = Path(filepath).expanduser().resolve(strict=False)
        else:
            target, path_error = validate_path_in_roots(
                filepath, allow_missing=False, must_be_dir=False,
                allowed_suffixes={".srt"}, label="Fichier SRT",
            )
            if path_error:
                return {"error": path_error}

        raw = target.read_bytes()
        detected = chardet.detect(raw)
        enc = detected.get("encoding") or "utf-8"
        text = raw.decode(enc, errors="replace")

        def _shift_timestamp(match):
            h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            total_ms = (h * 3600 + m * 60 + s) * 1000 + ms + offset_ms
            if total_ms < 0:
                total_ms = 0
            new_h = total_ms // 3600000
            new_m = (total_ms % 3600000) // 60000
            new_s = (total_ms % 60000) // 1000
            new_ms = total_ms % 1000
            return f"{new_h:02d}:{new_m:02d}:{new_s:02d},{new_ms:03d}"

        timing_re = re.compile(
            r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})"
        )

        lines_shifted = 0

        def _replace_line(m):
            nonlocal lines_shifted
            start = _SRT_TS_RE.sub(_shift_timestamp, m.group(1))
            end = _SRT_TS_RE.sub(_shift_timestamp, m.group(2))
            lines_shifted += 1
            return f"{start} --> {end}"

        result_text = timing_re.sub(_replace_line, text)

        target.write_text(result_text, encoding="utf-8")
        logger.info("[subtitle_tools] Shifted %s by %sms (%s lines)", filepath, offset_ms, lines_shifted)

        return {
            "success": True,
            "path": str(target),
            "offset_ms": offset_ms,
            "lines_shifted": lines_shifted,
        }

    except Exception:
        logger.exception("[subtitle_tools] Shift failed for %r", filepath)
        return {"error": "shift_failed"}
