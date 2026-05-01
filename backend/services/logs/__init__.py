"""
Service de management des files de logs Mediakeeper.
Package split into modules (Rule 9, <= 300 lines).

- Write in des files .txt in LOG_DIR
- Rotation weekly (each lundi)
- Deux types : mediakeeper.txt (applicatif) et emby.txt (API Emby)
"""
from ._config import (
    EMBY_LOG,
    LOG_DIR,
    MAX_LOG_FILES,
    MAX_LOG_LINES,
    MEDIAKEEPER_LOG,
    _format_size,
    ensure_log_dir,
)
from ._emby_fetch import fetch_and_store_emby_logs
from ._files import get_log_filepath, get_log_files, read_log_file, write_log_line
from ._rotation import _cleanup_old_log_files, rotate_logs_if_needed

__all__ = [
    "LOG_DIR",
    "MEDIAKEEPER_LOG",
    "EMBY_LOG",
    "MAX_LOG_LINES",
    "MAX_LOG_FILES",
    "ensure_log_dir",
    "get_log_files",
    "read_log_file",
    "get_log_filepath",
    "write_log_line",
    "rotate_logs_if_needed",
    "fetch_and_store_emby_logs",
    "_cleanup_old_log_files",
    "_format_size",
]
