"""Tests for /api/auth/login et /api/auth/portal-login."""
from unittest.mock import AsyncMock, patch

import pytest

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.user import User


@pytest.mark.asyncio
async def test_login_missing_fields(client):
    """POST /api/auth/login without body doit returnr 422."""
    resp = await client.post("/api/auth/login")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_bad_credentials(client):
    """POST /api/auth/login with mauvais credentials doit returnr 401."""
    resp = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrong_password",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_admin_success(client, admin_user):
    """POST /api/auth/login with le compte admin doit functionner."""
    resp = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_login_imported_emby_user_is_blocked(client, db_session):
    """Le mot de passe sentinelle Emby ne doit never open le backoffice."""
    db_session.add(User(
        username="emby-user",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    ))
    await db_session.commit()

    resp = await client.post("/api/auth/login", json={
        "username": "emby-user",
        "password": EXTERNAL_AUTH_PASSWORD_SENTINEL,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_portal_login_admin_gets_backoffice_and_portal_cookies(client, admin_user):
    """Le login portail doit open les deux surfaces for un admin."""
    resp = await client.post("/api/auth/portal-login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })

    assert resp.status_code == 200
    assert resp.json()["scope"] == "admin"
    assert client.cookies.get("mk_token")
    assert client.cookies.get("rq_token")


@pytest.mark.asyncio
async def test_portal_login_emby_user_redirects_to_portal(client, db_session):
    """The portal login must accept an imported Emby account without opening the backoffice."""
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
            "token": "rq-test-token",
            "user": user,
            "profile": profile,
        }),
    ), patch(
        "api.auth._portal.get_unread_news",
        new=AsyncMock(return_value=[]),
    ):
        resp = await client.post("/api/auth/portal-login", json={
            "username": "emby-user",
            "password": "emby-password",
        })

    assert resp.status_code == 200
    assert resp.json()["scope"] == "portal"
    assert resp.json()["profile"]["display_name"] == "Emby User"
    assert client.cookies.get("mk_token") is None
    assert client.cookies.get("rq_token") == "rq-test-token"


@pytest.mark.asyncio
async def test_portal_login_emby_user_sets_csrf_cookie(raw_client, db_session):
    """Le parcours portail Demandes doit aussi bootstrapper le cookie CSRF."""
    user = User(
        username="emby-csrf-user",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="Emby CSRF User",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    assert raw_client.cookies.get("mk_csrf") is None

    with patch(
        "api.auth.login.authenticate_emby_user",
        new=AsyncMock(return_value={
            "token": "rq-csrf-token",
            "user": user,
            "profile": profile,
        }),
    ), patch(
        "api.auth._portal.get_unread_news",
        new=AsyncMock(return_value=[]),
    ):
        resp = await raw_client.post("/api/auth/portal-login", json={
            "username": "emby-csrf-user",
            "password": "emby-password",
        })

    assert resp.status_code == 200
    assert resp.json()["scope"] == "portal"
    assert raw_client.cookies.get("rq_token") == "rq-csrf-token"
    assert raw_client.cookies.get("mk_csrf")


@pytest.mark.asyncio
async def test_portal_login_admin_allowlisted_user_can_fallback_to_emby(client, db_session):
    """Un username allowlist admin doit encore pouvoir entrer in Demandes via Emby."""
    user = User(
        username="admin",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="Admin Emby",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    with patch(
        "api.auth.login.authenticate_emby_user",
        new=AsyncMock(return_value={
            "token": "rq-admin-emby-token",
            "user": user,
            "profile": profile,
        }),
    ), patch(
        "api.auth._portal.get_unread_news",
        new=AsyncMock(return_value=[]),
    ):
        resp = await client.post("/api/auth/portal-login", json={
            "username": "admin",
            "password": "emby-password",
        })

    assert resp.status_code == 200
    assert resp.json()["scope"] == "portal"
    assert client.cookies.get("mk_token") is None
    assert client.cookies.get("rq_token") == "rq-admin-emby-token"


@pytest.mark.asyncio
async def test_portal_login_emby_user_tolerates_post_login_service_failures(client, db_session):
    """The portal must still open Requests even if news/UI flags fail."""
    user = User(
        username="emby-safe-user",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="Safe User",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    with patch(
        "api.auth.login.authenticate_emby_user",
        new=AsyncMock(return_value={
            "token": "rq-safe-token",
            "user": user,
            "profile": profile,
        }),
    ), patch(
        "api.auth._portal.get_unread_news",
        new=AsyncMock(side_effect=RuntimeError("news unavailable")),
    ), patch(
        "api.auth._portal.get_portal_flag",
        new=AsyncMock(side_effect=RuntimeError("settings unavailable")),
    ):
        resp = await client.post("/api/auth/portal-login", json={
            "username": "emby-safe-user",
            "password": "emby-password",
        })

    assert resp.status_code == 200
    assert resp.json()["scope"] == "portal"
    assert resp.json()["unread_news_count"] == 0
    assert resp.json()["ui"]["show_requests_tab"] is True
    assert client.cookies.get("rq_token") == "rq-safe-token"


@pytest.mark.asyncio
async def test_portal_login_emby_user_survives_xp_rollback(client, db_session):
    """Un rollback XP ne doit pas expirer les objets au point de faire planter le login."""
    user = User(
        username="emby-xp-user",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="XP User",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    async def _rollback_xp(db, user_id):
        await db.rollback()
        return None

    with patch(
        "api.auth.login.authenticate_emby_user",
        new=AsyncMock(return_value={
            "token": "rq-xp-token",
            "user": user,
            "profile": profile,
        }),
    ), patch(
        "api.auth._portal.get_unread_news",
        new=AsyncMock(return_value=[]),
    ), patch(
        "services.portal.xp.grant_daily_login_xp",
        new=AsyncMock(side_effect=_rollback_xp),
    ):
        resp = await client.post("/api/auth/portal-login", json={
            "username": "emby-xp-user",
            "password": "emby-password",
        })

    assert resp.status_code == 200
    assert resp.json()["scope"] == "portal"
    assert resp.json()["username"] == "emby-xp-user"
    assert resp.json()["profile"]["display_name"] == "XP User"
    assert client.cookies.get("rq_token") == "rq-xp-token"
