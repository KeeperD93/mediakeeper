"""Configuration : LOG_DIR, constantes, helpers."""
import logging
import os
from pathlib import Path

logger = logging.getLogger("mediakeeper.logs")

_portable_logs = Path(__file__).resolve().parent.parent.parent / "logs"
_log_dir_env = os.getenv("LOG_DIR", "").strip()
_data_logs = Path("/data/logs")
_app_logs = Path("/app/logs")

if _log_dir_env:
    LOG_DIR = Path(_log_dir_env)
elif _data_logs.parent.exists():
    LOG_DIR = _data_logs
elif _app_logs.parent.exists():
    LOG_DIR = _app_logs
else:
    LOG_DIR = _portable_logs

MEDIAKEEPER_LOG = "mediakeeper.txt"
EMBY_LOG = "emby.txt"
MAX_LOG_LINES = 30000
MAX_LOG_FILES = 10


def ensure_log_dir():
    """Create the log directory if it does not exist."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _format_size(size_bytes: int) -> str:
    """Formate une size en octets en format readable."""
    if size_bytes < 1024:
        return f"{size_bytes} o"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} Ko"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} Mo"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} Go"
