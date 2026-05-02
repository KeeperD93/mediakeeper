"""Tests for the runtime monitoring webhook (services.monitoring.webhook)."""
from unittest.mock import AsyncMock, patch

import pytest

from services.monitoring import (
    DEBOUNCE_WINDOW_SEC,
    AlertType,
    reset_debounce_state,
    send_alert,
)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_debounce_state()
    yield
    reset_debounce_state()


@pytest.mark.asyncio
async def test_send_alert_noop_when_webhook_unset(monkeypatch):
    """Without ``MK_DISCORD_ALERT_WEBHOOK`` set, the call is a silent no-op."""
    monkeypatch.delenv("MK_DISCORD_ALERT_WEBHOOK", raising=False)
    with patch("services.monitoring.webhook.send_discord_webhook", new=AsyncMock(return_value=True)) as send:
        result = await send_alert(AlertType.DB_UNAVAILABLE, {"reason": "test"})
    assert result is False
    send.assert_not_called()


@pytest.mark.asyncio
async def test_send_alert_posts_payload(monkeypatch):
    """When configured, send_alert posts a Discord-shaped payload."""
    monkeypatch.setenv("MK_DISCORD_ALERT_WEBHOOK", "https://example.invalid/webhook/test")
    captured: dict = {}

    async def _fake_send(url: str, payload: dict) -> bool:
        captured["url"] = url
        captured["payload"] = payload
        return True

    with patch("services.monitoring.webhook.send_discord_webhook", new=_fake_send):
        result = await send_alert(
            AlertType.SCHEDULER_TASK_CRASHED,
            {"task": "watchlist_scan", "error": "boom"},
            version="9.9.9",
        )

    assert result is True
    assert captured["url"] == "https://example.invalid/webhook/test"
    payload = captured["payload"]
    assert payload["username"] == "MediaKeeper"
    assert len(payload["embeds"]) == 1
    embed = payload["embeds"][0]
    assert embed["title"] == "Scheduler task crashed"
    assert embed["color"] == 0xE74C3C
    field_names = {f["name"] for f in embed["fields"]}
    assert {"version", "task", "error"}.issubset(field_names)


@pytest.mark.asyncio
async def test_send_alert_debounces_same_type(monkeypatch):
    """Two consecutive alerts of the same type collapse into one delivery."""
    monkeypatch.setenv("MK_DISCORD_ALERT_WEBHOOK", "https://example.invalid/webhook/test")
    with patch("services.monitoring.webhook.send_discord_webhook", new=AsyncMock(return_value=True)) as send:
        first = await send_alert(AlertType.DB_UNAVAILABLE, {"n": 1})
        second = await send_alert(AlertType.DB_UNAVAILABLE, {"n": 2})

    assert first is True
    assert second is False
    assert send.await_count == 1


@pytest.mark.asyncio
async def test_send_alert_does_not_debounce_different_types(monkeypatch):
    """Distinct alert types are tracked independently."""
    monkeypatch.setenv("MK_DISCORD_ALERT_WEBHOOK", "https://example.invalid/webhook/test")
    with patch("services.monitoring.webhook.send_discord_webhook", new=AsyncMock(return_value=True)) as send:
        await send_alert(AlertType.DB_UNAVAILABLE, {"n": 1})
        await send_alert(AlertType.SCHEDULER_TASK_CRASHED, {"task": "x"})
        await send_alert(AlertType.BACKUP_FAILED, {"component": "pg_dump"})

    assert send.await_count == 3


@pytest.mark.asyncio
async def test_send_alert_swallows_http_failures(monkeypatch, caplog):
    """A failing webhook never raises and never re-triggers an alert."""
    monkeypatch.setenv("MK_DISCORD_ALERT_WEBHOOK", "https://example.invalid/webhook/test")

    async def _broken(url: str, payload: dict) -> bool:
        raise RuntimeError("network down")

    with patch("services.monitoring.webhook.send_discord_webhook", new=_broken):
        with caplog.at_level("WARNING", logger="mediakeeper.monitoring"):
            result = await send_alert(AlertType.DB_UNAVAILABLE)

    assert result is False
    assert any("delivery failed" in rec.message for rec in caplog.records)


def test_debounce_window_is_thirty_minutes():
    """The contract advertised in docs/operations/monitoring.md is 30 minutes."""
    assert DEBOUNCE_WINDOW_SEC == 30 * 60
