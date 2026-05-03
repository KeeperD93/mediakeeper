"""Tests for the premium ``/api/portal/admin/users/*`` surface."""
from __future__ import annotations

import pytest

from core.security import create_access_token
from models.portal.profile import UserProfile


def _auth(client, admin_user) -> None:
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


@pytest.mark.asyncio
async def test_role_presets_endpoint(client, admin_user):
    _auth(client, admin_user)
    resp = await client.get("/api/portal/admin/users/role-presets")
    assert resp.status_code == 200
    body = resp.json()
    assert body["roles"] == ["viewer", "moderator", "admin"]
    assert "permissions" in body and "presets" in body


@pytest.mark.asyncio
async def test_list_users_filters(client, admin_user, db_session):
    """List endpoint should respect the ``source`` filter."""
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()

    _auth(client, admin_user)
    resp = await client.get("/api/portal/admin/users?source=local")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["source"] == "local"
    assert items[0]["permissions"]["can_chat"] is True
    assert items[0]["online"] is False


@pytest.mark.asyncio
async def test_create_local_user_then_role_change(client, admin_user, db_session):
    """End-to-end happy path: create local + flip role + audit trail recorded."""
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()

    _auth(client, admin_user)

    resp = await client.post("/api/portal/admin/users/local", json={
        "username": "alice",
        "password": "supersecret",
        "display_name": "Alice",
        "email": "alice@example.com",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    profile_id = body["profile_id"]

    # Detail
    resp = await client.get(f"/api/portal/admin/users/{profile_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["source"] == "local"
    assert detail["display_name"] == "Alice"

    # Role change applies the preset
    resp = await client.patch(
        f"/api/portal/admin/users/{profile_id}/role",
        json={"role": "moderator"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "moderator"

    # Audit trail recorded
    resp = await client.get(f"/api/portal/admin/users/{profile_id}/audit")
    assert resp.status_code == 200
    actions = [item["action"] for item in resp.json()["items"]]
    assert "user.created" in actions
    assert "user.role_changed" in actions


@pytest.mark.asyncio
async def test_soft_delete_then_restore(client, admin_user, db_session):
    """Soft delete must keep the row but flag it; restore reverses."""
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()

    _auth(client, admin_user)

    resp = await client.post("/api/portal/admin/users/local", json={
        "username": "bob",
        "password": "supersecret",
    })
    assert resp.status_code == 200
    profile_id = resp.json()["profile_id"]

    # Delete (soft)
    resp = await client.delete(f"/api/portal/admin/users/{profile_id}")
    assert resp.status_code == 200

    # Default list hides soft-deleted users
    resp = await client.get("/api/portal/admin/users")
    assert resp.status_code == 200
    assert all(it["id"] != profile_id for it in resp.json()["items"])

    # include_deleted=true brings them back
    resp = await client.get("/api/portal/admin/users?include_deleted=true")
    assert resp.status_code == 200
    assert any(it["id"] == profile_id for it in resp.json()["items"])

    # Restore
    resp = await client.post(f"/api/portal/admin/users/{profile_id}/restore")
    assert resp.status_code == 200

    resp = await client.get("/api/portal/admin/users")
    assert any(it["id"] == profile_id for it in resp.json()["items"])


@pytest.mark.asyncio
async def test_bulk_set_role(client, admin_user, db_session):
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()

    _auth(client, admin_user)

    ids = []
    for username in ("carol", "dave"):
        resp = await client.post("/api/portal/admin/users/local", json={
            "username": username,
            "password": "supersecret",
        })
        assert resp.status_code == 200
        ids.append(resp.json()["profile_id"])

    resp = await client.post("/api/portal/admin/users/bulk", json={
        "action": "set_role",
        "profile_ids": ids,
        "payload": {"role": "moderator"},
    })
    assert resp.status_code == 200
    assert resp.json()["processed"] == 2

    for profile_id in ids:
        resp = await client.get(f"/api/portal/admin/users/{profile_id}")
        assert resp.status_code == 200
        assert resp.json()["role"] == "moderator"


@pytest.mark.asyncio
async def test_unauthenticated_request_is_rejected(raw_client):
    """No mk_token cookie → 401, no leak of the route surface."""
    resp = await raw_client.get("/api/portal/admin/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_csrf_required_on_mutations(raw_client, admin_user, db_session):
    """A PATCH without the CSRF header must be rejected, even with auth."""
    db_session.add(UserProfile(
        user_id=admin_user.id, display_name="Admin", role="admin",
        source="local", account_active=True,
    ))
    await db_session.commit()
    raw_client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))
    resp = await raw_client.patch(
        "/api/portal/admin/users/1/role",
        json={"role": "moderator"},
    )
    assert resp.status_code in (403, 419, 401)


@pytest.mark.asyncio
async def test_self_soft_delete_is_blocked(client, admin_user, db_session):
    """An admin must never be able to soft-delete their own account."""
    profile = UserProfile(
        user_id=admin_user.id, display_name="Admin", role="admin",
        source="local", account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    _auth(client, admin_user)
    resp = await client.delete(f"/api/portal/admin/users/{profile.id}")
    assert resp.status_code == 200
    assert resp.json().get("error") == "self_action_forbidden"


@pytest.mark.asyncio
async def test_self_deactivate_is_blocked(client, admin_user, db_session):
    """Same protection on the active toggle so the admin cannot lock
    themselves out without recourse."""
    profile = UserProfile(
        user_id=admin_user.id, display_name="Admin", role="admin",
        source="local", account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    _auth(client, admin_user)
    resp = await client.patch(
        f"/api/portal/admin/users/{profile.id}/active",
        json={"active": False},
    )
    assert resp.status_code == 200
    assert resp.json().get("error") == "self_action_forbidden"


@pytest.mark.asyncio
async def test_extend_access_sets_end_date(client, admin_user, db_session):
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()

    _auth(client, admin_user)
    resp = await client.post("/api/portal/admin/users/local", json={
        "username": "eve",
        "password": "supersecret",
    })
    profile_id = resp.json()["profile_id"]

    resp = await client.post(
        f"/api/portal/admin/users/{profile_id}/extend-access",
        json={"months": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["access_end_date"] is not None
