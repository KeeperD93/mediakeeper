"""Read and write MediaKeeper log files."""
from datetime import datetime, timezone
from pathlib import Path
import re

from ._config import (
    EMBY_LOG,
    LOG_DIR,
    MEDIAKEEPER_LOG,
    _format_size,
    ensure_log_dir,
    logger,
)

_LOG_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}\.txt$")


def _safe_log_path(filename: str) -> Path | None:
    if not _LOG_FILENAME_RE.fullmatch(filename or ""):
        return None
    root = LOG_DIR.resolve(strict=False)
    candidate = (root / filename).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def get_log_files() -> list[dict]:
    """
    Return the list of log files with metadata.
    Sorted by descending modification date.
    """
    ensure_log_dir()
    files = []
    for f in LOG_DIR.iterdir():
        if f.is_file() and f.suffix == ".txt":
            stat = f.stat()
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "size_label": _format_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "modified_label": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%d/%m/%Y %H:%M"),
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


def read_log_file(filename: str, lines: int = 200) -> dict:
    """
    Read the last N lines of a log file (newest first).
    Return content and metadata.
    """
    filepath = _safe_log_path(filename)
    if filepath is None:
        return {"error": "invalid_filename", "lines": [], "total_lines": 0}

    if not filepath.is_file():
        return {"error": "file_not_found", "lines": [], "total_lines": 0}

    try:
        from collections import deque
        total = 0
        last_lines = deque(maxlen=lines)
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                total += 1
                last_lines.append(line.rstrip("\n\r"))

        result_lines = list(reversed(last_lines))

        stat = filepath.stat()
        return {
            "filename": filename,
            "lines": result_lines,
            "total_lines": total,
            "size": stat.st_size,
            "size_label": _format_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        }
    except Exception:
        logger.exception("[logs] read log file failed for %r", filename)
        return {"error": "log_read_failed", "lines": [], "total_lines": 0}


def get_log_filepath(filename: str) -> Path | None:
    """Return the full path of a log file for download."""
    filepath = _safe_log_path(filename)
    if filepath is None:
        return None
    if filepath.is_file():
        return filepath
    return None


def write_log_line(log_type: str, message: str):
    """
    Write a log line to the appropriate file.
    log_type: 'mediakeeper' or 'emby'
    """
    ensure_log_dir()
    filename = MEDIAKEEPER_LOG if log_type == "mediakeeper" else EMBY_LOG
    filepath = LOG_DIR / filename
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {message}\n")
    except Exception:
        logger.exception("[logs] write log line failed for %r", filename)
