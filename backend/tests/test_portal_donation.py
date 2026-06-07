"""Operator donation link surfaced on the heart panel.

Covers the settings storage (free-text, NOT locale-normalised), the admin
PATCH endpoint (alias + http(s) validation + extra="forbid"), and the
``ui.donation`` block that every portal user reads from ``/auth/me``.
"""
import pytest

from services.portal.admin import get_portal_settings, update_portal_settings
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

_SETTINGS = "/api/portal/admin/settings"
_ME = "/api/portal/auth/me"


@pytest.mark.asyncio
async def test_service_round_trip_preserves_url_and_message(db_session):
    await update_portal_settings(db_session, {
        "portal.donation.enabled": True,
        "portal.donation.url": "https://ko-fi.com/keeperd93",
        "portal.donation.message": "Merci de soutenir l'instance !",
    })
    s = await get_portal_settings(db_session)
    assert s["portal.donation.enabled"] is True
    # Free-text must NOT be locale-normalised (that would wreck the URL).
    assert s["portal.donation.url"] == "https://ko-fi.com/keeperd93"
    assert s["portal.donation.message"] == "Merci de soutenir l'instance !"


@pytest.mark.asyncio
async def test_service_drops_non_http_url(db_session):
    await update_portal_settings(db_session, {"portal.donation.url": "javascript:alert(1)"})
    assert (await get_portal_settings(db_session))["portal.donation.url"] == ""


@pytest.mark.asyncio
async def test_service_caps_message_length(db_session):
    await update_portal_settings(db_session, {"portal.donation.message": "x" * 600})
    assert len((await get_portal_settings(db_session))["portal.donation.message"]) == 500


@pytest.mark.asyncio
async def test_patch_sets_donation_via_alias(client, db_session):
    user, _ = await make_portal_user(db_session, username="da", display_name="DA", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.patch(_SETTINGS, json={
        "donation.enabled": True,
        "donation.url": "https://example.org/give",
        "donation.message": "Support us",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["donation.enabled"] is True
    assert body["donation.url"] == "https://example.org/give"
    assert body["donation.message"] == "Support us"


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
    })
    user, _ = await make_portal_user(db_session, username="viewer1", display_name="V")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    r = await client.get(_ME)
    assert r.status_code == 200, r.text
    donation = r.json()["ui"]["donation"]
    assert donation["enabled"] is True
    assert donation["url"] == "https://ko-fi.com/keeperd93"
    assert donation["message"] == "Thanks"


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
