"""Tests for the admin GDPR settings endpoints (Phase 11B Phase 2).

Covers:

* GET returns the five values with disabling defaults out of the box.
* PUT persists partial updates, leaves untouched keys alone.
* Privacy texts pass through ``sanitize_html`` (script blocks dropped).
* Delay range enforced by Pydantic (7 ≤ n ≤ 90) — 422 outside.
* Unknown keys rejected by ``extra="forbid"``.
"""
import pytest

from core.security import create_access_token
from models.portal.profile import UserProfile
from services.settings import get_setting, set_setting


def _auth(client, admin_user) -> None:
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


async def _admin_profile(db_session, admin_user) -> None:
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_returns_disabling_defaults_when_settings_unset(
    client, admin_user, db_session,
):
    await _admin_profile(db_session, admin_user)
    _auth(client, admin_user)

    resp = await client.get("/api/portal/admin/gdpr/settings")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["enabled"] is False
    assert body["dpo_contact"] == ""
    assert body["account_purge_delay_days"] == 30
    assert body["privacy_text_fr"] == ""
    assert body["privacy_text_en"] == ""


@pytest.mark.asyncio
async def test_get_reflects_persisted_values(client, admin_user, db_session):
    await _admin_profile(db_session, admin_user)
    await set_setting(db_session, "gdpr.enabled", "true")
    await set_setting(db_session, "gdpr.dpo_contact", "operator@example.org")
    await set_setting(db_session, "gdpr.account_purge_delay_days", "45")
    _auth(client, admin_user)

    resp = await client.get("/api/portal/admin/gdpr/settings")
    body = resp.json()
    assert body["enabled"] is True
    assert body["dpo_contact"] == "operator@example.org"
    assert body["account_purge_delay_days"] == 45


@pytest.mark.asyncio
async def test_put_partial_update_only_sent_keys(client, admin_user, db_session):
    await _admin_profile(db_session, admin_user)
    await set_setting(db_session, "gdpr.dpo_contact", "before")
    _auth(client, admin_user)

    resp = await client.put(
        "/api/portal/admin/gdpr/settings",
        json={"enabled": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["enabled"] is True
    # Untouched key stays.
    assert body["dpo_contact"] == "before"


@pytest.mark.asyncio
async def test_put_privacy_text_passes_through_sanitize_html(
    client, admin_user, db_session,
):
    """The canonical safety boundary must run on every admin write.
    Sending a ``<script>`` block stays out of the persisted value."""
    await _admin_profile(db_session, admin_user)
    _auth(client, admin_user)

    payload_html = "<p>Policy</p><script>alert(1)</script>"
    resp = await client.put(
        "/api/portal/admin/gdpr/settings",
        json={"privacy_text_fr": payload_html},
    )
    assert resp.status_code == 200, resp.text
    persisted = await get_setting(db_session, "gdpr.privacy_text_fr")
    assert "<script" not in persisted
    assert "alert" not in persisted
    assert "<p>Policy</p>" in persisted


@pytest.mark.asyncio
async def test_put_delay_above_cap_rejected(client, admin_user, db_session):
    await _admin_profile(db_session, admin_user)
    _auth(client, admin_user)

    resp = await client.put(
        "/api/portal/admin/gdpr/settings",
        json={"account_purge_delay_days": 365},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_delay_below_floor_rejected(client, admin_user, db_session):
    await _admin_profile(db_session, admin_user)
    _auth(client, admin_user)

    resp = await client.put(
        "/api/portal/admin/gdpr/settings",
        json={"account_purge_delay_days": 1},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_rejects_unknown_keys(client, admin_user, db_session):
    """A stale frontend or a probe must not slip arbitrary settings
    through this endpoint."""
    await _admin_profile(db_session, admin_user)
    _auth(client, admin_user)

    resp = await client.put(
        "/api/portal/admin/gdpr/settings",
        json={"enabled": True, "rogue_key": "evil"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_requires_csrf(raw_client, admin_user, db_session):
    """``raw_client`` skips CSRF cookie seeding — the PUT must reject."""
    await _admin_profile(db_session, admin_user)
    _auth(raw_client, admin_user)

    resp = await raw_client.put(
        "/api/portal/admin/gdpr/settings",
        json={"enabled": True},
    )
    assert resp.status_code in (401, 403)
