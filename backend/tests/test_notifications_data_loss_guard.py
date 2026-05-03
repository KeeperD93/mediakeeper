"""Anti data-loss guards on /api/notifications/*/config endpoints.

Posting a config payload with no webhooks (Discord) or an empty
client_secret (Imgur) used to silently overwrite the previously-saved
encrypted values whenever a partially-filled admin form was submitted.

The endpoints now refuse such payloads with HTTP 409 unless the caller
acknowledges the clear via ``confirm_clear: true`` (Discord) or the
appropriate flag (Imgur, covered separately).
"""
from __future__ import annotations

import json

import pytest

from services.settings import get_notification_channel, set_notification_channel


async def _login(client) -> None:
    r = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


async def _seed_existing_discord_config(db_session) -> None:
    """Persist a Discord config with one webhook so the guard has
    something to protect."""
    payload = {
        "enabled": True,
        "delay": 10,
        "image_host": "emby",
        "webhooks": [
            {
                "id": "wh-1",
                "name": "default",
                "url": "https://discord.com/api/webhooks/000/seeded",
                "enabled": True,
                "events": {},
                "templates": {},
                "settings": {},
                "image_host": "emby",
            }
        ],
    }
    await set_notification_channel(db_session, "discord", json.dumps(payload))


@pytest.mark.asyncio
async def test_discord_config_empty_webhooks_rejected_409(
    client, admin_user, db_session,
):
    """POST with ``webhooks: []`` against an existing non-empty config
    must be refused so a partial form does not destroy the encrypted
    URLs already saved."""
    await _login(client)
    await _seed_existing_discord_config(db_session)

    r = await client.post("/api/notifications/discord/config", json={
        "enabled": False,
        "webhooks": [],
    })

    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "discord_config_empty_webhooks_requires_confirm_clear"

    raw = await get_notification_channel(db_session, "discord")
    saved = json.loads(raw)
    assert len(saved["webhooks"]) == 1
    assert saved["webhooks"][0]["url"].endswith("/seeded")


@pytest.mark.asyncio
async def test_discord_config_normal_save_ok(
    client, admin_user, db_session,
):
    """A normal save with at least one webhook keeps the existing
    behaviour: 200 OK and the new payload is persisted."""
    await _login(client)
    await _seed_existing_discord_config(db_session)

    r = await client.post("/api/notifications/discord/config", json={
        "enabled": True,
        "delay": 15,
        "image_host": "emby",
        "webhooks": [
            {
                "id": "wh-1",
                "name": "default",
                "url": "https://discord.com/api/webhooks/000/updated",
                "enabled": True,
                "events": {"added": True},
                "templates": {},
                "settings": {},
                "image_host": "emby",
            }
        ],
    })

    assert r.status_code == 200, r.text
    raw = await get_notification_channel(db_session, "discord")
    saved = json.loads(raw)
    assert saved["delay"] == 15
    assert saved["webhooks"][0]["url"].endswith("/updated")
    # The flag must never be persisted alongside the channel payload.
    assert "confirm_clear" not in saved


@pytest.mark.asyncio
async def test_discord_config_clear_with_confirm_flag_ok(
    client, admin_user, db_session,
):
    """An explicit ``confirm_clear: true`` lets the admin wipe every
    saved webhook (legitimate when migrating to a different channel)."""
    await _login(client)
    await _seed_existing_discord_config(db_session)

    r = await client.post("/api/notifications/discord/config", json={
        "enabled": False,
        "webhooks": [],
        "confirm_clear": True,
    })

    assert r.status_code == 200, r.text
    raw = await get_notification_channel(db_session, "discord")
    saved = json.loads(raw)
    assert saved["webhooks"] == []
    assert "confirm_clear" not in saved


async def _seed_existing_imgur_config(db_session) -> None:
    payload = {
        "client_id": "id-seeded",
        "client_secret": "secret-seeded",
    }
    await set_notification_channel(db_session, "imgur", json.dumps(payload))


@pytest.mark.asyncio
async def test_imgur_config_empty_secret_rejected_409(
    client, admin_user, db_session,
):
    """POST with a blank ``client_secret`` and no ``client_secret_configured``
    flag must be refused — that combination would have silently wiped
    the encrypted Imgur key out of the channel store."""
    await _login(client)
    await _seed_existing_imgur_config(db_session)

    r = await client.post("/api/notifications/imgur/config", json={
        "client_id": "id-seeded",
        "client_secret": "",
    })

    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "imgur_config_empty_secret_requires_confirm_clear"

    raw = await get_notification_channel(db_session, "imgur")
    saved = json.loads(raw)
    assert saved["client_secret"] == "secret-seeded"


@pytest.mark.asyncio
async def test_imgur_config_normal_save_ok(
    client, admin_user, db_session,
):
    """A normal save with a fresh ``client_secret`` keeps the existing
    behaviour: 200 OK and the new payload is persisted."""
    await _login(client)
    await _seed_existing_imgur_config(db_session)

    r = await client.post("/api/notifications/imgur/config", json={
        "client_id": "id-rotated",
        "client_secret": "secret-rotated",
    })

    assert r.status_code == 200, r.text
    raw = await get_notification_channel(db_session, "imgur")
    saved = json.loads(raw)
    assert saved["client_id"] == "id-rotated"
    assert saved["client_secret"] == "secret-rotated"
    assert "confirm_clear" not in saved


@pytest.mark.asyncio
async def test_imgur_config_clear_with_confirm_flag_ok(
    client, admin_user, db_session,
):
    """An explicit ``confirm_clear: true`` lets the admin wipe the
    encrypted secret (legitimate when rotating to a brand-new app)."""
    await _login(client)
    await _seed_existing_imgur_config(db_session)

    r = await client.post("/api/notifications/imgur/config", json={
        "client_id": "",
        "client_secret": "",
        "confirm_clear": True,
    })

    assert r.status_code == 200, r.text
    raw = await get_notification_channel(db_session, "imgur")
    saved = json.loads(raw)
    assert saved["client_secret"] == ""


@pytest.mark.asyncio
async def test_imgur_config_masked_resave_preserves_secret(
    client, admin_user, db_session,
):
    """Re-saving the form right after a GET re-renders the masked
    secret as ``client_secret=""`` plus ``client_secret_configured=True``.
    The merge must restore the existing secret and the new guard must
    not fire — otherwise every settings tweak would 409."""
    await _login(client)
    await _seed_existing_imgur_config(db_session)

    r = await client.post("/api/notifications/imgur/config", json={
        "client_id": "id-tweaked",
        "client_secret": "",
        "client_secret_configured": True,
    })

    assert r.status_code == 200, r.text
    raw = await get_notification_channel(db_session, "imgur")
    saved = json.loads(raw)
    assert saved["client_id"] == "id-tweaked"
    assert saved["client_secret"] == "secret-seeded"
