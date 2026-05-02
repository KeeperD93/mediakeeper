"""Send runtime alerts to a Discord-compatible webhook with in-memory debounce.

Design notes:

- The webhook URL is read from ``MK_DISCORD_ALERT_WEBHOOK`` at every send
  so operators can rotate it without restarting the container. When the
  variable is unset (or empty), :func:`send_alert` returns silently — the
  feature is fully opt-in.
- A small in-memory dict tracks the last send timestamp per alert type
  and suppresses duplicates inside the debounce window. State is lost on
  restart, which is acceptable: a restart is itself a strong signal and
  the typical container uptime exceeds the debounce window.
- Failures of the webhook itself (timeout, HTTP error, exception) are
  logged once and swallowed. We never re-trigger an alert from inside
  the alert path, otherwise a flapping webhook would create an infinite
  loop.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from services.discord import send_discord_webhook

from .events import AlertType
from .payload import build_alert_payload

logger = logging.getLogger("mediakeeper.monitoring")

ENV_WEBHOOK_VAR = "MK_DISCORD_ALERT_WEBHOOK"
DEBOUNCE_WINDOW_SEC = 30 * 60
HTTP_TIMEOUT_SEC = 5.0

_last_sent: dict[AlertType, float] = {}
_lock = asyncio.Lock()


def _now() -> float:
    return time.monotonic()


def reset_debounce_state() -> None:
    """Clear the in-memory debounce state. Tests only."""
    _last_sent.clear()


async def send_alert(
    alert_type: AlertType,
    context: dict[str, Any] | None = None,
    *,
    version: str | None = None,
) -> bool:
    """Push a runtime alert to the configured webhook.

    Returns ``True`` if the payload was actually sent, ``False`` if the
    call was a no-op (webhook not configured, debounce hit) or if the
    HTTP delivery failed. Never raises.
    """
    webhook_url = os.getenv(ENV_WEBHOOK_VAR, "").strip()
    if not webhook_url:
        return False

    async with _lock:
        last = _last_sent.get(alert_type)
        now = _now()
        if last is not None and (now - last) < DEBOUNCE_WINDOW_SEC:
            return False
        _last_sent[alert_type] = now

    if version is None:
        try:
            from api.changelog import APP_VERSION

            version = APP_VERSION
        except Exception:
            version = "unknown"

    payload = build_alert_payload(alert_type, context, version)

    try:
        sent = await asyncio.wait_for(
            send_discord_webhook(webhook_url, payload),
            timeout=HTTP_TIMEOUT_SEC,
        )
    except Exception as exc:
        logger.warning("[monitoring] webhook delivery failed for %s: %s", alert_type.value, exc)
        return False

    if not sent:
        logger.warning("[monitoring] webhook rejected delivery for %s", alert_type.value)
    return bool(sent)
