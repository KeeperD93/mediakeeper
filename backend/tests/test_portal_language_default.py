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
