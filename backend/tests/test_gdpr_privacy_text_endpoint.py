"""HTTP-level tests for ``GET /api/portal/me/privacy-text``.

Covers:

* gating (404 when ``gdpr.enabled`` is ``false``),
* locale resolution (``?lang=`` overrides profile.language),
* unknown ``?lang`` collapses to the profile language fallback,
* DPO contact propagation,
* empty defaults when admin has not configured a language yet.
"""
import pytest

from services.settings import set_setting
from tests._portal_profile_helpers import (
    PORTAL_COOKIE,
    make_portal_user,
    portal_token,
)


async def _enable_gdpr(db_session) -> None:
    await set_setting(db_session, "gdpr.enabled", "true")


async def _seed_user(client, db_session, *, username="reader", language="fr"):
    user, profile = await make_portal_user(
        db_session, username=username, role="viewer"
    )
    profile.language = language
    db_session.add(profile)
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(username))
    return user, profile


@pytest.mark.asyncio
async def test_returns_404_when_gdpr_disabled(client, db_session):
    await _seed_user(client, db_session, username="pt-off")
    resp = await client.get("/api/portal/me/privacy-text")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Not found"}


@pytest.mark.asyncio
async def test_returns_french_text_for_french_profile(client, db_session):
    await _enable_gdpr(db_session)
    await set_setting(db_session, "gdpr.privacy_text_fr", "<p>Bonjour</p>")
    await set_setting(db_session, "gdpr.privacy_text_en", "<p>Hello</p>")
    await set_setting(db_session, "gdpr.dpo_contact", "dpo@example.org")
    await _seed_user(client, db_session, username="pt-fr", language="fr")

    resp = await client.get("/api/portal/me/privacy-text")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lang"] == "fr"
    assert body["text_html"] == "<p>Bonjour</p>"
    assert body["dpo_contact"] == "dpo@example.org"


@pytest.mark.asyncio
async def test_query_param_overrides_profile_language(client, db_session):
    await _enable_gdpr(db_session)
    await set_setting(db_session, "gdpr.privacy_text_fr", "<p>FR</p>")
    await set_setting(db_session, "gdpr.privacy_text_en", "<p>EN</p>")
    await _seed_user(client, db_session, username="pt-mix", language="fr")

    resp = await client.get("/api/portal/me/privacy-text?lang=en")
    assert resp.status_code == 200
    body = resp.json()
    assert body["lang"] == "en"
    assert body["text_html"] == "<p>EN</p>"


@pytest.mark.asyncio
async def test_unknown_lang_falls_back_to_profile_language(client, db_session):
    await _enable_gdpr(db_session)
    await set_setting(db_session, "gdpr.privacy_text_fr", "<p>FR</p>")
    await set_setting(db_session, "gdpr.privacy_text_en", "<p>EN</p>")
    await _seed_user(client, db_session, username="pt-bad", language="en")

    resp = await client.get("/api/portal/me/privacy-text?lang=zz")
    body = resp.json()
    # Bad ``?lang`` is ignored — profile language wins.
    assert body["lang"] == "en"
    assert body["text_html"] == "<p>EN</p>"


@pytest.mark.asyncio
async def test_returns_empty_strings_when_admin_has_not_configured_yet(
    client, db_session,
):
    await _enable_gdpr(db_session)
    await _seed_user(client, db_session, username="pt-empty", language="fr")

    resp = await client.get("/api/portal/me/privacy-text")
    body = resp.json()
    assert body["text_html"] == ""
    assert body["dpo_contact"] == ""
