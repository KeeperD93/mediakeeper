"""Integration tests confirming Pydantic config models reject unknown keys.

Each :func:`test_*_rejects_unknown_field` posts a body that adds a single
extra key on top of an otherwise valid payload and asserts a 422 with the
``extra_forbidden`` discriminator from Pydantic v2.
"""
from unittest.mock import patch

import pytest

from core.security import create_access_token


def _auth_admin(client, admin_user):
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


def _has_extra_forbidden_error(detail) -> bool:
    if not isinstance(detail, list):
        return False
    return any(item.get("type") == "extra_forbidden" for item in detail)


@pytest.mark.asyncio
async def test_discord_config_rejects_unknown_field(client, admin_user):
    _auth_admin(client, admin_user)
    resp = await client.post(
        "/api/notifications/discord/config",
        json={
            "enabled": True,
            "delay": 10,
            "image_host": "emby",
            "webhooks": [],
            "confirm_clear": True,
            "rogue_field": "should_be_rejected",
        },
    )
    assert resp.status_code == 422
    assert _has_extra_forbidden_error(resp.json().get("detail"))


@pytest.mark.asyncio
async def test_imgur_config_rejects_unknown_field(client, admin_user):
    _auth_admin(client, admin_user)
    resp = await client.post(
        "/api/notifications/imgur/config",
        json={
            "client_id": "abc",
            "client_secret": "shh",
            "client_secret_configured": True,
            "client_secret_length": 0,
            "confirm_clear": True,
            "extra_admin_only_flag": True,
        },
    )
    assert resp.status_code == 422
    assert _has_extra_forbidden_error(resp.json().get("detail"))


@pytest.mark.asyncio
async def test_healthcheck_config_rejects_unknown_field(client, admin_user):
    _auth_admin(client, admin_user)
    resp = await client.put(
        "/api/healthcheck/config",
        json={
            "obsolete_codecs_enabled": True,
            "obsolete_containers_enabled": True,
            "low_resolution_enabled": True,
            "min_resolution_height": 720,
            "low_bitrate_enabled": True,
            "min_video_bitrate_kbps": 1000,
            "no_audio_enabled": True,
            "large_file_enabled": True,
            "max_file_size_gb": 50,
            "hdr_no_sdr_enabled": True,
            "stealth_drift_field": "leak",
        },
    )
    assert resp.status_code == 422
    assert _has_extra_forbidden_error(resp.json().get("detail"))


@pytest.mark.asyncio
async def test_notif_rules_config_rejects_unknown_field(client, admin_user):
    _auth_admin(client, admin_user)
    resp = await client.post(
        "/api/notifications/rules",
        json={
            "dnd_enabled": False,
            "dnd_start": "23:00",
            "dnd_end": "07:00",
            "library_filter": [],
            "min_resolution": "",
            "genre_filter": [],
            "shadow_dnd_zone": "should_be_rejected",
        },
    )
    assert resp.status_code == 422
    assert _has_extra_forbidden_error(resp.json().get("detail"))


@pytest.mark.asyncio
async def test_restore_request_rejects_unknown_field(client, admin_user):
    """Forbid covers the from-disk restore as well as the upload variant."""
    _auth_admin(client, admin_user)
    with patch(
        "api.backup._restore._validate_uploaded_backup_archive",
        return_value=None,
    ), patch(
        "api.backup._restore.get_backup_path",
        return_value=None,  # Pydantic 422 fires before we ever look at the file.
    ):
        resp = await client.post(
            "/api/backup/restore",
            json={
                "filename": "x.zip",
                "components": {},
                "drop_database": True,  # not a real field
            },
        )
    assert resp.status_code == 422
    assert _has_extra_forbidden_error(resp.json().get("detail"))


@pytest.mark.asyncio
async def test_legitimate_config_save_still_succeeds(client, admin_user):
    """Forbid must not break a payload that only carries declared fields."""
    _auth_admin(client, admin_user)
    resp = await client.post(
        "/api/notifications/discord/config",
        json={
            "enabled": False,
            "delay": 10,
            "image_host": "emby",
            "webhooks": [],
            "confirm_clear": True,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": True}
