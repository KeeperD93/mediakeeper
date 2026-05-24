"""Integration coverage for the CSRF cookie rotation contract.

Auth boundaries (admin login, portal-login, change-password) MUST
replace the ``mk_csrf`` cookie value carried by the incoming request,
closing the session-fixation window where a token pre-posed on a
victim's browser would otherwise survive the auth handshake.

Authenticated polls (``/me``, ``/refresh``) MUST preserve the current
``mk_csrf`` value so concurrent SPA requests do not see the
double-submit token shift under their feet.

These tests assert the contract at the HTTP surface so a future
refactor of the helpers cannot silently revert it.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.user import User


# A value that satisfies the allowlist regex so we know the change after
# rotation is driven by the rotation contract, not by the allowlist
# rejecting a malformed input.
_VALID_PRE_FIXED = "x" * 32
_ADMIN_PASSWORD = "TestPassword123!"


# Auth boundaries — cookie value MUST change


@pytest.mark.asyncio
async def test_admin_login_rotates_csrf_cookie(raw_client, admin_user):
    r = await raw_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": _ADMIN_PASSWORD},
        headers={"Cookie": f"mk_csrf={_VALID_PRE_FIXED}"},
    )

    assert r.status_code == 200, r.text
    new_value = raw_client.cookies.get("mk_csrf")
    assert new_value is not None
    assert new_value != _VALID_PRE_FIXED


@pytest.mark.asyncio
async def test_portal_login_admin_branch_rotates_csrf_cookie(raw_client, admin_user):
    r = await raw_client.post(
        "/api/auth/portal-login",
        json={"username": "admin", "password": _ADMIN_PASSWORD},
        headers={"Cookie": f"mk_csrf={_VALID_PRE_FIXED}"},
    )

    assert r.status_code == 200, r.text
    new_value = raw_client.cookies.get("mk_csrf")
    assert new_value is not None
    assert new_value != _VALID_PRE_FIXED


@pytest.mark.asyncio
async def test_portal_login_emby_branch_rotates_csrf_cookie(raw_client, db_session):
    """Imported Emby user falling into the cascade also gets a fresh token."""
    user = User(
        username="emby-user",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="Emby User",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    with patch(
        "api.auth.login.authenticate_emby_user",
        new=AsyncMock(return_value={
            "token": "rq-rotate-token",
            "user": user,
            "profile": profile,
        }),
    ), patch(
        "api.auth._portal.get_unread_news",
        new=AsyncMock(return_value=[]),
    ):
        r = await raw_client.post(
            "/api/auth/portal-login",
            json={"username": "emby-user", "password": "any"},
            headers={"Cookie": f"mk_csrf={_VALID_PRE_FIXED}"},
        )

    assert r.status_code == 200, r.text
    new_value = raw_client.cookies.get("mk_csrf")
    assert new_value is not None
    assert new_value != _VALID_PRE_FIXED


@pytest.mark.asyncio
async def test_portal_endpoint_login_rotates_csrf_cookie(raw_client, db_session):
    """``/api/portal/auth/login`` (Emby-only entry point) rotates as well."""
    user = User(
        username="portal-emby",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="Portal Emby",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    with patch(
        "api.portal.auth.authenticate_emby_user",
        new=AsyncMock(return_value={
            "token": "rq-portal-rotate-token",
            "user": user,
            "profile": profile,
        }),
    ):
        r = await raw_client.post(
            "/api/portal/auth/login",
            json={"username": "portal-emby", "password": "any"},
            headers={"Cookie": f"mk_csrf={_VALID_PRE_FIXED}"},
        )

    assert r.status_code == 200, r.text
    new_value = raw_client.cookies.get("mk_csrf")
    assert new_value is not None
    assert new_value != _VALID_PRE_FIXED


@pytest.mark.asyncio
async def test_change_password_rotates_csrf_cookie(raw_client, admin_user):
    """A successful password change must invalidate the previous CSRF token."""
    r = await raw_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": _ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    post_login_csrf = raw_client.cookies.get("mk_csrf")
    assert post_login_csrf is not None

    r = await raw_client.post(
        "/api/auth/change-password",
        headers={"X-CSRF-Token": post_login_csrf},
        json={
            "current_password": _ADMIN_PASSWORD,
            "new_password": "NewPassword456!",
            "confirm_password": "NewPassword456!",
        },
    )
    assert r.status_code == 200, r.text

    post_change_csrf = raw_client.cookies.get("mk_csrf")
    assert post_change_csrf is not None
    assert post_change_csrf != post_login_csrf


# Authenticated polls — cookie value MUST be preserved


@pytest.mark.asyncio
async def test_admin_me_preserves_csrf_cookie(raw_client, admin_user):
    r = await raw_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": _ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    post_login_csrf = raw_client.cookies.get("mk_csrf")
    assert post_login_csrf is not None

    r = await raw_client.get("/api/auth/me")
    assert r.status_code == 200, r.text

    post_me_csrf = raw_client.cookies.get("mk_csrf")
    assert post_me_csrf == post_login_csrf


@pytest.mark.asyncio
async def test_admin_refresh_preserves_csrf_cookie(raw_client, admin_user):
    r = await raw_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": _ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    post_login_csrf = raw_client.cookies.get("mk_csrf")
    assert post_login_csrf is not None

    r = await raw_client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": post_login_csrf},
    )
    assert r.status_code == 200, r.text

    post_refresh_csrf = raw_client.cookies.get("mk_csrf")
    assert post_refresh_csrf == post_login_csrf
