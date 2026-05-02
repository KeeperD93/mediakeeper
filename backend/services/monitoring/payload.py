"""Build Discord-compatible embed payloads for runtime alerts."""
from datetime import datetime, timezone
from typing import Any

from .events import ALERT_COLORS, ALERT_TITLES, AlertType

MAX_FIELD_VALUE_LEN = 1024
MAX_CONTEXT_FIELDS = 8


def _sanitize_value(value: Any) -> str:
    """Stringify and truncate a context value to keep the payload small and safe."""
    text = str(value)
    if len(text) > MAX_FIELD_VALUE_LEN:
        text = text[: MAX_FIELD_VALUE_LEN - 3] + "..."
    return text


def build_alert_payload(
    alert_type: AlertType,
    context: dict[str, Any] | None,
    version: str,
) -> dict:
    """Return a Discord-compatible JSON body for the given alert.

    The payload sticks to fields that are safe to publish: alert title,
    severity color, declared app version, ISO-UTC timestamp and a small
    bag of caller-provided context (truncated to avoid leaking large
    tracebacks or runtime internals).
    """
    fields = [{"name": "version", "value": _sanitize_value(version), "inline": True}]
    if context:
        for key, value in list(context.items())[:MAX_CONTEXT_FIELDS]:
            fields.append({"name": str(key), "value": _sanitize_value(value), "inline": True})

    embed = {
        "title": ALERT_TITLES[alert_type],
        "color": ALERT_COLORS[alert_type],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": fields,
    }
    return {"username": "MediaKeeper", "embeds": [embed]}
