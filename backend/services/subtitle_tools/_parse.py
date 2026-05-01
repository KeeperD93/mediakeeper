"""SRT parsing: timestamp regex + metadata extraction."""
import re

import chardet

# Regex for timestamps SRT : 00:01:23,456
_SRT_TS_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")
_SUBTITLE_FILE_EXTENSIONS = {".srt", ".sub", ".ssa", ".ass", ".vtt", ".idx"}


def _ts_to_seconds(match) -> float:
    """Convertit un match de timestamp SRT en secondes."""
    h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
    return h * 3600 + m * 60 + s + ms / 1000.0


def _format_ts(seconds: float) -> str:
    """Formate des secondes en HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_srt_metadata(content: bytes) -> dict:
    """Parse an SRT file and return its metadata.

    Return:
        line_count, first_ts, last_ts, duration_sec, encoding, size.
    """
    detected = chardet.detect(content)
    encoding = detected.get("encoding") or "utf-8"
    confidence = detected.get("confidence") or 0

    try:
        text = content.decode(encoding, errors="replace")
    except Exception:
        text = content.decode("utf-8", errors="replace")
        encoding = "utf-8"

    timestamps = _SRT_TS_RE.findall(text)
    if not timestamps:
        return {
            "line_count": 0,
            "first_ts": "00:00:00",
            "last_ts": "00:00:00",
            "duration_sec": 0,
            "encoding": encoding,
            "encoding_confidence": round(confidence, 2),
            "size": len(content),
        }

    # Approximation: number of timestamps / 2 (start + end per block)
    line_count = len(timestamps) // 2

    first_match = re.search(_SRT_TS_RE, text)
    all_matches = list(re.finditer(_SRT_TS_RE, text))
    last_match = all_matches[-1] if all_matches else first_match

    first_sec = _ts_to_seconds(first_match) if first_match else 0
    last_sec = _ts_to_seconds(last_match) if last_match else 0

    return {
        "line_count": line_count,
        "first_ts": _format_ts(first_sec),
        "last_ts": _format_ts(last_sec),
        "duration_sec": round(last_sec - first_sec, 1),
        "encoding": encoding,
        "encoding_confidence": round(confidence, 2),
        "size": len(content),
    }
