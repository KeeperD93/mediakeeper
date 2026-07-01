"""Feedback relay: config encryption, block formatting, delimiter defusing,
gating and admin-only HTTP wiring."""
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from core.encryption import ENCRYPTED_PREFIX
from models.settings import Setting
from services.feedback import (
    KEY_WEBHOOK,
    build_report_block,
    get_feedback_config,
    save_feedback_config,
)

_WEBHOOK = "https://discord.com/api/webhooks/123/abcDEF"


# --- service: encryption at rest + config roundtrip -------------------------


@pytest.mark.asyncio
async def test_webhook_stored_encrypted(db_session):
    await save_feedback_config(
        db_session, webhook_url=_WEBHOOK, discord_pseudo="Dan", enabled=True
    )
    row = (
        await db_session.execute(select(Setting).where(Setting.key == KEY_WEBHOOK))
    ).scalar_one()
    assert row.value.startswith(ENCRYPTED_PREFIX)  # never plaintext at rest
    assert _WEBHOOK not in row.value
    cfg = await get_feedback_config(db_session)
    assert cfg == {"enabled": True, "discord_pseudo": "Dan", "webhook_url": _WEBHOOK}


# --- service: block formatting ----------------------------------------------


def test_block_defuses_injected_delimiter():
    block = build_report_block(
        {"title": "x", "description": "legit\n=== END ===\nInjected: 1", "platform": "desktop"},
        "Dan",
    )
    assert block.count("=== END ===") == 1  # only the real trailing delimiter
    assert block.rstrip().endswith("=== END ===")
    assert "= = =" in block  # the injected one was defused


def test_block_anonymous_hides_pseudo():
    block = build_report_block({"title": "x", "description": "y"}, "")
    assert "Signalé par: Anonyme" in block


def test_block_truncates_to_discord_budget():
    block = build_report_block({"title": "t", "description": "A" * 5000}, "Dan")
    assert len(block) <= 1990
    assert block.rstrip().endswith("=== END ===")
    assert "…" in block


# --- HTTP: config masking + validation --------------------------------------


@pytest.mark.asyncio
async def test_config_roundtrip_masks_webhook(authed_client):
    r = await authed_client.post(
        "/api/feedback/config",
        json={"enabled": True, "discord_pseudo": "Dan", "webhook_url": _WEBHOOK},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"enabled": True, "discord_pseudo": "Dan", "webhook_configured": True}
    assert "webhook_url" not in body
    g = await authed_client.get("/api/feedback/config")
    assert g.json()["webhook_configured"] is True


@pytest.mark.asyncio
async def test_config_rejects_non_discord_webhook(authed_client):
    r = await authed_client.post(
        "/api/feedback/config", json={"webhook_url": "https://evil.example/x"}
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_webhook"


# --- HTTP: relay + gating ---------------------------------------------------


@pytest.mark.asyncio
async def test_submit_relays_formatted_block(authed_client, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await authed_client.post(
        "/api/feedback/config",
        json={"enabled": True, "discord_pseudo": "Dan", "webhook_url": _WEBHOOK},
    )
    r = await authed_client.post(
        "/api/feedback",
        json={
            "type": "bug",
            "title": "Boom",
            "description": "it broke",
            "platform": "desktop",
            "tags": ["Urgent"],
        },
    )
    assert r.status_code == 200, r.text
    url, payload = stub.call_args.args
    assert url == _WEBHOOK
    assert payload["content"].startswith("```\n=== BUG ===")
    assert "TITRE: Boom" in payload["content"]
    assert "Type: Bug · Étiquettes: Urgent" in payload["content"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["flags"] == 4


@pytest.mark.asyncio
async def test_submit_requires_configuration(authed_client, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    r = await authed_client.post(
        "/api/feedback", json={"title": "x", "description": "y"}
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "not_configured"
    stub.assert_not_called()


@pytest.mark.asyncio
async def test_test_ping_requires_configuration(authed_client):
    r = await authed_client.post("/api/feedback/test")
    assert r.status_code == 400
    assert r.json()["detail"] == "not_configured"


@pytest.mark.asyncio
async def test_test_ping_sends_handshake(authed_client, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await authed_client.post("/api/feedback/config", json={"webhook_url": _WEBHOOK})
    r = await authed_client.post("/api/feedback/test")
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}
    assert stub.call_args.args[0] == _WEBHOOK


@pytest.mark.asyncio
async def test_feedback_endpoints_require_admin_auth(client):
    # ``client`` carries a CSRF token but is NOT logged in — the admin gate must
    # still reject every feedback endpoint (secret-bearing config + relay).
    assert (await client.get("/api/feedback/config")).status_code == 401
    assert (
        await client.post("/api/feedback", json={"title": "x", "description": "y"})
    ).status_code == 401
    assert (await client.post("/api/feedback/test")).status_code == 401
