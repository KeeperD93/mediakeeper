"""Per-user portal language as an override of an instance-wide default.

``user_profiles.language`` is nullable: NULL inherits the instance default
(settings key ``portal.default_language``, falling back to MK_DEFAULT_LOCALE).
GET/PUT ``/me`` expose the raw ``language`` plus the resolved
``effective_language``; sending ``language: null`` clears back to inherit.
"""
from __future__ import annotations

import pytest

from services.settings import get_portal_default_language, set_setting
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

_ME = "/api/portal/profiles/me"


@pytest.mark.asyncio
async def test_default_language_helper_falls_back_then_reads_setting(db_session):
    assert await get_portal_default_language(db_session) == "fr"  # unset -> MK_DEFAULT_LOCALE
    await set_setting(db_session, "portal.default_language", "en")
    assert await get_portal_default_language(db_session) == "en"


@pytest.mark.asyncio
async def test_get_me_inherit_resolves_to_instance_default(client, db_session):
    user, profile = await make_portal_user(db_session, username="alice", display_name="Alice")
    profile.language = None
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.get(_ME)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["language"] is None
    assert body["effective_language"] == "fr"  # no setting -> fallback


@pytest.mark.asyncio
async def test_get_me_explicit_language_is_kept(client, db_session):
    user, profile = await make_portal_user(db_session, username="bob", display_name="Bob")
    profile.language = "en"
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.get(_ME)
    body = resp.json()
    assert body["language"] == "en"
    assert body["effective_language"] == "en"


@pytest.mark.asyncio
async def test_get_me_inherits_configured_instance_default(client, db_session):
    await set_setting(db_session, "portal.default_language", "en")
    user, profile = await make_portal_user(db_session, username="carol", display_name="Carol")
    profile.language = None
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.get(_ME)
    assert resp.json()["effective_language"] == "en"


@pytest.mark.asyncio
async def test_put_me_null_clears_to_inherit(client, db_session):
    user, profile = await make_portal_user(db_session, username="dave", display_name="Dave")
    profile.language = "en"
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.put(_ME, json={"language": None})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["language"] is None
    assert body["effective_language"] == "fr"


@pytest.mark.asyncio
async def test_put_me_sets_explicit_language(client, db_session):
    user, profile = await make_portal_user(db_session, username="erin", display_name="Erin")
    profile.language = None
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.put(_ME, json={"language": "en"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["language"] == "en"


@pytest.mark.asyncio
async def test_portal_default_language_admin_round_trip(db_session):
    # Admin save path normalises (en-US -> en), get_portal_settings returns it,
    # the helper resolves it, and blank clears back to the MK_DEFAULT_LOCALE inherit.
    from services.portal.admin import get_portal_settings, update_portal_settings

    await update_portal_settings(db_session, {"portal.default_language": "en-US"})
    assert (await get_portal_settings(db_session))["portal.default_language"] == "en"
    assert await get_portal_default_language(db_session) == "en"
    await update_portal_settings(db_session, {"portal.default_language": ""})
    assert await get_portal_default_language(db_session) == "fr"


@pytest.mark.asyncio
async def test_discord_system_lang_follows_instance_default(db_session):
    # Discord system messages now use the instance default, not the first-active-user
    # heuristic.
    from services.discord.payloads import _resolve_system_lang
    from services.portal.admin import update_portal_settings

    assert await _resolve_system_lang(db_session) == "fr"
    await update_portal_settings(db_session, {"portal.default_language": "en"})
    assert await _resolve_system_lang(db_session) == "en"


@pytest.mark.asyncio
async def test_auth_me_exposes_effective_language(client, db_session):
    # The portal auth /me profile carries effective_language so PortalLayout can
    # apply the inherited instance default on portal entry (not just /profiles/me).
    from services.portal.admin import update_portal_settings

    user, profile = await make_portal_user(db_session, username="frank", display_name="Frank")
    profile.language = None
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    r = await client.get("/api/portal/auth/me")
    assert r.status_code == 200, r.text
    assert r.json()["profile"]["effective_language"] == "fr"

    await update_portal_settings(db_session, {"portal.default_language": "en"})
    r2 = await client.get("/api/portal/auth/me")
    assert r2.json()["profile"]["effective_language"] == "en"
