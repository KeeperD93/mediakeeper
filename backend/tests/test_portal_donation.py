"""Operator donation link surfaced on the heart panel.

Covers the settings storage (free-text, NOT locale-normalised), the admin
PATCH endpoint (alias + http(s) validation + extra="forbid"), and the
``ui.donation`` block that every portal user reads from ``/auth/me``.
"""
import pytest

from core.security import create_access_token
from services.portal.admin import get_portal_settings, update_portal_settings
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

_SETTINGS = "/api/portal/admin/settings"
_ME = "/api/portal/auth/me"
_BACKOFFICE = "/api/settings/donation"


@pytest.mark.asyncio
async def test_service_round_trip_preserves_url_and_message(db_session):
    await update_portal_settings(db_session, {
        "portal.donation.enabled": True,
        "portal.donation.url": "https://ko-fi.com/keeperd93",
        "portal.donation.message": "Merci de soutenir l'instance !",
        "portal.donation.button_label": "Payer mon café",
    })
    s = await get_portal_settings(db_session)
    assert s["portal.donation.enabled"] is True
    # Free-text must NOT be locale-normalised (that would wreck the URL).
    assert s["portal.donation.url"] == "https://ko-fi.com/keeperd93"
    assert s["portal.donation.message"] == "Merci de soutenir l'instance !"
    assert s["portal.donation.button_label"] == "Payer mon café"


@pytest.mark.asyncio
async def test_message_html_is_sanitised(db_session):
    # Rich text is kept, but scripts are stripped through the bleach pipeline.
    await update_portal_settings(db_session, {
        "portal.donation.message": "<strong>Merci</strong><script>alert(1)</script>",
    })
    stored = (await get_portal_settings(db_session))["portal.donation.message"]
    assert "<strong>Merci</strong>" in stored
    assert "<script" not in stored
    assert "alert(1)" not in stored


@pytest.mark.asyncio
async def test_message_empty_html_normalised_to_blank(db_session):
    # An emptied editor emits "<p></p>"; it must round-trip to "" so the
    # frontend falls back to its default text.
    await update_portal_settings(db_session, {"portal.donation.message": "<p></p>"})
    assert (await get_portal_settings(db_session))["portal.donation.message"] == ""


@pytest.mark.asyncio
async def test_service_drops_non_http_url(db_session):
    await update_portal_settings(db_session, {"portal.donation.url": "javascript:alert(1)"})
    assert (await get_portal_settings(db_session))["portal.donation.url"] == ""


@pytest.mark.asyncio
async def test_service_caps_message_length(db_session):
    # The rich-text message is capped at 4000 raw chars before sanitising.
    await update_portal_settings(db_session, {"portal.donation.message": "x" * 5000})
    assert len((await get_portal_settings(db_session))["portal.donation.message"]) == 4000


@pytest.mark.asyncio
async def test_patch_sets_donation_via_alias(client, db_session):
    user, _ = await make_portal_user(db_session, username="da", display_name="DA", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.patch(_SETTINGS, json={
        "donation.enabled": True,
        "donation.url": "https://example.org/give",
        "donation.message": "Support us",
        "donation.button_label": "Buy me a coffee",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["donation.enabled"] is True
    assert body["donation.url"] == "https://example.org/give"
    assert body["donation.message"] == "Support us"
    assert body["donation.button_label"] == "Buy me a coffee"


@pytest.mark.asyncio
async def test_patch_rejects_non_http_url(client, db_session):
    user, _ = await make_portal_user(db_session, username="db", display_name="DB", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.patch(_SETTINGS, json={"donation.url": "ftp://nope"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_me_ui_exposes_donation_when_enabled(client, db_session):
    await update_portal_settings(db_session, {
        "portal.donation.enabled": True,
        "portal.donation.url": "https://ko-fi.com/keeperd93",
        "portal.donation.message": "Thanks",
        "portal.donation.button_label": "Tip me",
    })
    user, _ = await make_portal_user(db_session, username="viewer1", display_name="V")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    r = await client.get(_ME)
    assert r.status_code == 200, r.text
    donation = r.json()["ui"]["donation"]
    assert donation["enabled"] is True
    assert donation["url"] == "https://ko-fi.com/keeperd93"
    assert donation["message"] == "Thanks"
    assert donation["button_label"] == "Tip me"


@pytest.mark.asyncio
async def test_backoffice_donation_endpoint(client, admin_user, db_session):
    # The dashboard top-bar heart reads the donation config from a backoffice
    # endpoint (main app auth), returning the same shape as ui.donation.
    await update_portal_settings(db_session, {
        "portal.donation.enabled": True,
        "portal.donation.url": "https://ko-fi.com/keeperd93",
        "portal.donation.button_label": "Tip me",
    })
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )
    r = await client.get(_BACKOFFICE)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert body["url"] == "https://ko-fi.com/keeperd93"
    assert body["button_label"] == "Tip me"


@pytest.mark.asyncio
async def test_me_ui_donation_hidden_when_enabled_but_no_url(client, db_session):
    # Flag on but no link set -> still reported disabled, nothing leaked.
    await update_portal_settings(db_session, {"portal.donation.enabled": True})
    user, _ = await make_portal_user(db_session, username="viewer2", display_name="V2")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    r = await client.get(_ME)
    donation = r.json()["ui"]["donation"]
    assert donation["enabled"] is False
    assert donation["url"] == ""
    assert donation["message"] == ""
    assert donation["button_label"] == ""
