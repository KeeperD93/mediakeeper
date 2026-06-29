"""Portal maintenance mode — anonymous read + locale routing."""
import pytest

from models.settings import Setting
from services.portal import maintenance as maintenance_svc


@pytest.mark.asyncio
async def test_get_maintenance_anonymous_returns_state(client):
    """The public endpoint must be reachable without any session cookie."""
    response = await client.get("/api/portal/maintenance")
    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload and "text" in payload
    assert isinstance(payload["enabled"], bool)
    assert isinstance(payload["text"], str)


@pytest.mark.asyncio
async def test_is_maintenance_enabled_reads_setting(db_session):
    assert await maintenance_svc.is_maintenance_enabled(db_session) is False

    db_session.add(Setting(key="maintenance.enabled", value="true"))
    await db_session.commit()
    assert await maintenance_svc.is_maintenance_enabled(db_session) is True

    row = await db_session.get(Setting, 1)
    if row and row.key == "maintenance.enabled":
        row.value = "false"
        await db_session.commit()


@pytest.mark.asyncio
async def test_get_maintenance_text_locale_routing(db_session):
    db_session.add(Setting(key="maintenance.text_fr", value="Texte FR"))
    db_session.add(Setting(key="maintenance.text_en", value="EN text"))
    await db_session.commit()

    assert await maintenance_svc.get_maintenance_text(db_session, "") == "Texte FR"
    assert await maintenance_svc.get_maintenance_text(db_session, "fr-FR") == "Texte FR"
    assert await maintenance_svc.get_maintenance_text(db_session, "en") == "EN text"
    assert await maintenance_svc.get_maintenance_text(db_session, "en-US") == "EN text"


@pytest.mark.asyncio
async def test_get_maintenance_state_via_accept_language(client, db_session):
    db_session.add(Setting(key="maintenance.text_fr", value="FR"))
    db_session.add(Setting(key="maintenance.text_en", value="EN"))
    await db_session.commit()

    fr = await client.get("/api/portal/maintenance")
    en = await client.get(
        "/api/portal/maintenance",
        headers={"Accept-Language": "en-US"},
    )
    assert fr.status_code == 200 and en.status_code == 200
    assert fr.json()["text"] == "FR"
    assert en.json()["text"] == "EN"


@pytest.mark.asyncio
async def test_update_maintenance_settings_persists(db_session):
    refreshed = await maintenance_svc.update_maintenance_settings(
        db_session,
        enabled=True,
        text_fr="Custom FR",
        text_en="Custom EN",
    )
    assert refreshed["enabled"] is True
    assert refreshed["text_fr"] == "Custom FR"
    assert refreshed["text_en"] == "Custom EN"

    assert await maintenance_svc.is_maintenance_enabled(db_session) is True

    # Idempotent partial update.
    refreshed = await maintenance_svc.update_maintenance_settings(
        db_session, enabled=False
    )
    assert refreshed["enabled"] is False
    assert refreshed["text_fr"] == "Custom FR"


@pytest.mark.asyncio
async def test_portal_module_login_refuses_member_during_maintenance(client, db_session):
    """The Emby-only /api/portal/login enforces the same maintenance gate as
    /api/auth/portal-login: a member is refused while maintenance is on."""
    from unittest.mock import AsyncMock, patch

    from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
    from models.portal.profile import UserProfile
    from models.user import User

    user = User(
        username="emby-portal-maint",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id, display_name="Portal Maint", role="viewer", account_active=True,
    )
    db_session.add(profile)
    db_session.add(Setting(key="maintenance.enabled", value="true"))
    await db_session.commit()
    await db_session.refresh(profile)

    with patch(
        "api.portal.auth.authenticate_emby_user",
        new=AsyncMock(return_value={"token": "t", "user": user, "profile": profile}),
    ):
        resp = await client.post("/api/portal/auth/login", json={
            "username": "emby-portal-maint",
            "password": "x",
        })

    assert resp.status_code == 403
    assert resp.json()["detail"] == "maintenance"
