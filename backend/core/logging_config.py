"""
Structured JSON logging for Mediakeeper.
Used when MK_DEBUG=false (production).
In debug mode the classic text format is kept for readability.
"""

import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format logs as JSON, one line per entry."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_method"):
            log_entry["method"] = record.request_method
        if hasattr(record, "request_path"):
            log_entry["path"] = record.request_path
        return json.dumps(log_entry, ensure_ascii=False)
