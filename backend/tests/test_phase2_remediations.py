import json
from unittest.mock import ANY, AsyncMock, patch

import pytest

from core.security import create_access_token, hash_password
from models.user import User
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from services.settings import MASKED_SECRET_LENGTH, get_notification_channel, get_setting


async def _create_user_with_profile(
    db_session,
    *,
    username: str,
    role: str = "viewer",
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password=hash_password("TestPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username.title(),
        role=role,
        account_active=True,
        chat_enabled=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


@pytest.mark.asyncio
async def test_portal_request_contracts_split_admin_and_user(client, admin_user, db_session):
    admin_profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        account_active=True,
        chat_enabled=True,
    )
    db_session.add(admin_profile)
    await db_session.commit()

    viewer, _ = await _create_user_with_profile(db_session, username="viewer")
    other, _ = await _create_user_with_profile(db_session, username="other")

    first = MediaRequest(
        user_id=viewer.id,
        tmdb_id=10,
        media_type="movie",
        title="Safe Request",
        status="pending",
    )
    second = MediaRequest(
        user_id=other.id,
        tmdb_id=11,
        media_type="movie",
        title="Rejected Request",
        status="rejected",
        reject_reason="Already blocked",
        requested_by_admin=admin_user.id,
    )
    db_session.add_all([first, second])
    await db_session.commit()

    client.cookies.set("rq_token", create_access_token({"sub": viewer.username, "scope": "portal"}))
    user_resp = await client.get("/api/portal/requests")

    assert user_resp.status_code == 200
    user_items = user_resp.json()["items"]
    assert {item["title"] for item in user_items} == {"Safe Request", "Rejected Request"}
    assert all("user_id" not in item for item in user_items)
    assert all("reject_reason" not in item for item in user_items)
    assert all("requested_by_admin" not in item for item in user_items)

    client.cookies.set("rq_token", create_access_token({"sub": admin_user.username, "scope": "portal"}))
    admin_resp = await client.get("/api/portal/requests/admin")

    assert admin_resp.status_code == 200
    admin_items = admin_resp.json()["items"]
    rejected = next(item for item in admin_items if item["title"] == "Rejected Request")
    assert rejected["user_id"] == other.id
    assert rejected["reject_reason"] == "Already blocked"
    assert rejected["requested_by_admin"] == admin_user.id


@pytest.mark.asyncio
async def test_onboarding_folders_are_optional_and_status_reflects_db(client, admin_user, db_session):
    """Folders are declared via the DB-backed settings (media_folders), and
    the ``steps.folders`` flag in ``/onboarding/status`` reflects that source
    of truth. ``/onboarding/complete`` does not require folders anymore:
    fresh installs pulled from GHCR ship with the media volumes commented
    out in ``docker-compose.prod.yml`` and would otherwise dead-end at the
    end of the wizard. Operators can declare folders later via Settings.
    """
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    status_before = await client.get("/api/onboarding/status")
    assert status_before.status_code == 200
    assert status_before.json()["steps"]["folders"] is False

    complete_without_folders = await client.post("/api/onboarding/complete")
    assert complete_without_folders.status_code == 200
    assert complete_without_folders.json()["success"] is True

    save_resp = await client.put("/api/settings/media-folders", json={
        "folders": [
            {"key": "MEDIA_FILMS", "label": "Films", "path": "/media/films"},
            {"key": "MEDIA_SERIES", "label": "Series", "path": "/media/series"},
        ]
    })
    assert save_resp.status_code == 200

    list_resp = await client.get("/api/settings/media-folders")
    assert list_resp.status_code == 200
    assert {item["label"] for item in list_resp.json()} == {"Films", "Series"}

    status_after = await client.get("/api/onboarding/status")
    assert status_after.status_code == 200
    assert status_after.json()["steps"]["folders"] is True


@pytest.mark.asyncio
async def test_onboarding_status_rejects_deactivated_admin(client, admin_user, db_session):
    """A deactivated admin's still-valid JWT can no longer read setup state —
    /status mirrors get_current_user's live checks (#393)."""
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    active = await client.get("/api/onboarding/status")
    assert active.json()["authenticated"] is True

    admin_user.is_active = False
    db_session.add(admin_user)
    await db_session.commit()

    revoked = await client.get("/api/onboarding/status")
    assert revoked.status_code == 200
    assert revoked.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_settings_tools_mask_secrets_and_preserve_partial_updates(client, admin_user, db_session):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    first_save = await client.post("/api/settings/tools/emby", json={
        "enabled": True,
        "url": "http://emby.local",
        "api_key": "super-secret-api-key-value",
    })
    assert first_save.status_code == 200

    get_resp = await client.get("/api/settings/tools")
    assert get_resp.status_code == 200
    emby = get_resp.json()["emby"]
    assert emby["url"] == "http://emby.local"
    assert emby["api_key"] == ""
    assert emby["api_key_configured"] is True
    # Fixed mask width, not the real secret length (length is not leaked).
    assert emby["api_key_length"] == MASKED_SECRET_LENGTH

    second_save = await client.post("/api/settings/tools/emby", json={
        "enabled": True,
        "url": "http://emby.internal",
    })
    assert second_save.status_code == 200

    assert await get_setting(db_session, "emby.api_key") == "super-secret-api-key-value"
    assert await get_setting(db_session, "emby.url") == "http://emby.internal"


@pytest.mark.asyncio
async def test_save_tool_rejects_unsafe_public_url(client, admin_user):
    """A javascript: public_url is rejected at the write edge — it would
    otherwise be re-served verbatim into "Watch on Emby" deep-links (#380)."""
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    resp = await client.post("/api/settings/tools/emby", json={
        "enabled": True,
        "url": "http://emby.local",
        "public_url": "javascript:alert(1)//",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_url_scheme"


@pytest.mark.asyncio
async def test_save_tool_accepts_valid_public_url(client, admin_user, db_session):
    """A valid https public_url is stored intact (#380)."""
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    resp = await client.post("/api/settings/tools/emby", json={
        "enabled": True,
        "url": "http://emby.local",
        "public_url": "https://emby.example.com",
    })
    assert resp.status_code == 200
    assert await get_setting(db_session, "emby.public_url") == "https://emby.example.com"


@pytest.mark.asyncio
async def test_notification_configs_mask_secrets_and_preserve_hidden_values(client, admin_user, db_session):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    discord_save = await client.post("/api/notifications/discord/config", json={
        "enabled": True,
        "delay": 15,
        "image_host": "imgur",
        "webhooks": [
            {
                "id": "wh-main",
                "name": "Main",
                "url": "https://discord.com/api/webhooks/1/token",
                "enabled": True,
            }
        ],
    })
    assert discord_save.status_code == 200

    discord_get = await client.get("/api/notifications/discord/config")
    assert discord_get.status_code == 200
    discord_cfg = discord_get.json()
    assert discord_cfg["webhooks"][0]["url"] == ""
    assert discord_cfg["webhooks"][0]["url_configured"] is True

    discord_update = await client.post("/api/notifications/discord/config", json={
        "enabled": True,
        "delay": 20,
        "image_host": "imgur",
        "webhooks": [
            {
                "id": "wh-main",
                "name": "Main",
                "url": "",
                "url_configured": True,
                "enabled": True,
            }
        ],
    })
    assert discord_update.status_code == 200

    stored_discord = json.loads(await get_notification_channel(db_session, "discord"))
    assert stored_discord["delay"] == 20
    assert stored_discord["webhooks"][0]["url"] == "https://discord.com/api/webhooks/1/token"

    imgur_save = await client.post("/api/notifications/imgur/config", json={
        "client_id": "imgur-id",
        "client_secret": "imgur-client-secret-value",
    })
    assert imgur_save.status_code == 200

    imgur_get = await client.get("/api/notifications/imgur/config")
    assert imgur_get.status_code == 200
    assert imgur_get.json()["client_secret"] == ""
    assert imgur_get.json()["client_secret_configured"] is True
    assert imgur_get.json()["client_secret_length"] == MASKED_SECRET_LENGTH

    imgur_update = await client.post("/api/notifications/imgur/config", json={
        "client_id": "imgur-id-2",
        "client_secret": "",
        "client_secret_configured": True,
    })
    assert imgur_update.status_code == 200

    stored_imgur = json.loads(await get_notification_channel(db_session, "imgur"))
    assert stored_imgur["client_id"] == "imgur-id-2"
    assert stored_imgur["client_secret"] == "imgur-client-secret-value"


@pytest.mark.asyncio
async def test_discord_test_can_use_stored_webhook_id(client, admin_user, db_session):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))

    await client.post("/api/notifications/discord/config", json={
        "enabled": True,
        "delay": 10,
        "image_host": "imgur",
        "webhooks": [
            {
                "id": "wh-main",
                "name": "Main",
                "url": "https://discord.com/api/webhooks/2/token",
                "enabled": True,
            }
        ],
    })

    with patch("api.notifications.send_discord_test", new=AsyncMock(return_value={"ok": True})) as mocked:
        resp = await client.post("/api/notifications/discord/test", json={
            "webhook_id": "wh-main",
            "wh_config": {},
            "test_type": "movie",
        })

    assert resp.status_code == 200
    mocked.assert_awaited_once_with("https://discord.com/api/webhooks/2/token", {}, "movie", ANY)
