"""CSRF middleware symmetry across the admin and portal cookies.

The double-submit guard must reject mutations that carry an auth
cookie but no matching ``X-CSRF-Token`` header — regardless of which
cookie (``mk_token`` admin / ``rq_token`` portal) opened the session.
The few admin routes that still depend on the legacy ``require_csrf``
exist for defence-in-depth; the global middleware is what enforces
the contract on portal routes.
"""
from __future__ import annotations

import pytest

from core.security import hash_password
from models.portal.profile import UserProfile


async def _admin_login(raw_client) -> None:
    """Open an admin session via the bare ``raw_client`` fixture so
    the resulting cookie state is the only thing carried into the
    follow-up mutation."""
    r = await raw_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_admin_mutation_without_csrf_header_returns_403(raw_client, admin_user):
    """An authenticated admin POST without the header is refused."""
    await _admin_login(raw_client)
    raw_client.cookies.delete("mk_csrf")

    r = await raw_client.post(
        "/api/auth/preferences",
        json={"theme": "dark"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_token_invalid"


@pytest.mark.asyncio
async def test_admin_mutation_with_mismatched_csrf_token_returns_403(raw_client, admin_user):
    """Header value differs from the cookie value — refused even when
    both are present."""
    await _admin_login(raw_client)
    raw_client.cookies.set("mk_csrf", "cookie-side")

    r = await raw_client.post(
        "/api/auth/preferences",
        headers={"X-CSRF-Token": "header-side"},
        json={"theme": "dark"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_token_invalid"


@pytest.mark.asyncio
async def test_portal_mutation_without_csrf_header_returns_403(raw_client, admin_user, db_session, portal_login):
    """Same shape on the portal cookie. Without the header the mutation
    is refused before the route handler runs — proving the global
    middleware enforces parity with the admin path."""
    await portal_login(raw_client)
    raw_client.cookies.delete("mk_csrf")

    # The admin profile was created on the fly by portal-login.
    profile = (
        await db_session.execute(
            UserProfile.__table__.select().where(UserProfile.user_id == admin_user.id)
        )
    ).first()
    assert profile is not None, "portal-login must auto-create the admin profile"

    r = await raw_client.put(
        "/api/portal/profiles/me",
        json={"display_name": "renamed"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_token_invalid"


@pytest.mark.asyncio
async def test_portal_mutation_with_mismatched_csrf_token_returns_403(raw_client, admin_user, portal_login):
    await portal_login(raw_client)
    raw_client.cookies.set("mk_csrf", "cookie-side")

    r = await raw_client.put(
        "/api/portal/profiles/me",
        headers={"X-CSRF-Token": "header-side"},
        json={"display_name": "renamed"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_token_invalid"


@pytest.mark.asyncio
async def test_unauthenticated_mutation_passes_csrf_to_auth_layer(raw_client):
    """Without any auth cookie the CSRF guard steps aside — the
    request is rejected by the auth dependency instead, which
    returns 401. This proves the symmetric short-circuit on both
    cookie shapes (no auth → no CSRF check)."""
    r = await raw_client.put(
        "/api/portal/profiles/me",
        json={"display_name": "renamed"},
    )
    assert r.status_code == 401
