"""Diagnostic log lines that surface deployment-mode hints.

Three signals:

* Boot summary — single INFO line printed on container start with the
  detected mode, the trusted-proxy CSV and the frontend allowlist.
* CSRF origin mismatch — first hostile cross-origin POST writes one
  WARN to logs (rate-limited 1/h) so an operator chasing a 403 has a
  doc pointer.
* WS upgrade fallback — an HTTP GET on the chat WS path returns 426
  and logs the same kind of operator hint.
"""
from __future__ import annotations

import time

import pytest


def test_log_deployment_mode_emits_summary_line(monkeypatch, caplog):
    import core.app_startup as startup
    monkeypatch.setenv("TRUSTED_PROXIES", "192.0.2.0/24")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://public.example")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    with caplog.at_level("INFO", logger="mediakeeper"):
        startup._log_deployment_mode()
    matching = [r for r in caplog.records if "deployment mode" in r.message]
    assert matching, "expected one INFO record"
    assert "B (reverse proxy)" in matching[0].getMessage()
    assert "https://public.example" in matching[0].getMessage()


def test_log_deployment_mode_reports_mode_a_when_no_proxy(monkeypatch, caplog):
    import core.app_startup as startup
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    with caplog.at_level("INFO", logger="mediakeeper"):
        startup._log_deployment_mode()
    matching = [r for r in caplog.records if "deployment mode" in r.message]
    assert matching
    msg = matching[0].getMessage()
    assert "A (direct LAN)" in msg
    assert "auto-derived" in msg


@pytest.mark.asyncio
async def test_csrf_origin_mismatch_writes_diagnostic_warn_once(client, admin_user, caplog):
    import core.csrf_middleware as mw
    mw._last_origin_mismatch_log = 0.0  # cooldown reset

    # Open the backoffice session.
    r = await client.post("/api/auth/login", json={
        "username": "admin", "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text

    with caplog.at_level("WARNING", logger="mediakeeper.csrf"):
        # First mismatch — should write the WARN.
        r1 = await client.post(
            "/api/auth/preferences",
            headers={"Origin": "https://evil.example"},
            json={"theme": "dark"},
        )
        # Second mismatch within the same hour — must be suppressed.
        r2 = await client.post(
            "/api/auth/preferences",
            headers={"Origin": "https://evil.example"},
            json={"theme": "dark"},
        )
    assert r1.status_code == 403
    assert r2.status_code == 403
    matching = [r for r in caplog.records if "origin mismatch" in r.message]
    assert len(matching) == 1, [r.message for r in matching]


@pytest.mark.asyncio
async def test_chat_ws_path_returns_426_on_http_get(raw_client, caplog):
    """A reverse proxy that drops the Upgrade header turns the WS
    handshake into a plain GET. The fallback handler answers with 426
    and writes one operator hint."""
    import api.portal.chat as chat_module
    chat_module._last_ws_upgrade_log = 0.0  # cooldown reset

    with caplog.at_level("WARNING", logger="mediakeeper.portal.chat"):
        resp = await raw_client.get("/api/portal/chat/ws/1")
    assert resp.status_code == 426
    assert resp.headers.get("Upgrade") == "websocket"
    matching = [r for r in caplog.records if "received an HTTP GET" in r.message]
    assert len(matching) == 1
