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
async def test_patch_identity_returns_persisted_detail(client, admin_user, db_session):
    """PATCH must persist the new identity AND return a payload whose
    `user` mirror matches the value that the subsequent GET serves.

    Regression for the admin "Edit user" form reverting to the previous
    value right after a successful save — root cause was the response
    lacking the persisted detail so the frontend had to race a refetch.
    """
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
        "username": "ellie",
        "password": "supersecret",
        "display_name": "Ellie",
        "email": "ellie@example.com",
    })
    assert resp.status_code == 200, resp.text
    profile_id = resp.json()["profile_id"]

    resp = await client.patch(
        f"/api/portal/admin/users/{profile_id}",
        json={
            "display_name": "Ellie Updated",
            "first_name": "Ellie",
            "last_name": "Smith",
            "email": "ellie.new@example.com",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert set(body["changed"]) == {"display_name", "first_name", "last_name", "email"}
    assert body["user"]["display_name"] == "Ellie Updated"
    assert body["user"]["first_name"] == "Ellie"
    assert body["user"]["last_name"] == "Smith"
    assert body["user"]["email"] == "ellie.new@example.com"

    resp = await client.get(f"/api/portal/admin/users/{profile_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["display_name"] == "Ellie Updated"
    assert detail["first_name"] == "Ellie"
    assert detail["last_name"] == "Smith"
    assert detail["email"] == "ellie.new@example.com"


@pytest.mark.asyncio
async def test_patch_identity_clears_field_when_empty_string(client, admin_user, db_session):
    """Empty string in first_name/last_name/email must persist as NULL
    (clear) — regression for the admin form where the previous value
    came back after Save because the frontend sent ``null`` and the
    service treated null as "no change". The fix sends ``""`` from the
    UI; the service interprets the stripped empty string as a clear."""
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
        "username": "frank",
        "password": "supersecret",
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "frank@example.com",
    })
    assert resp.status_code == 200, resp.text
    profile_id = resp.json()["profile_id"]

    resp = await client.patch(
        f"/api/portal/admin/users/{profile_id}",
        json={"first_name": "", "last_name": "", "email": ""},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["first_name"] is None
    assert body["user"]["last_name"] is None
    assert body["user"]["email"] is None
    assert set(body["changed"]) == {"first_name", "last_name", "email"}

    resp = await client.get(f"/api/portal/admin/users/{profile_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["first_name"] is None
    assert detail["last_name"] is None
    assert detail["email"] is None


@pytest.mark.asyncio
async def test_patch_identity_rejects_empty_display_name(client, admin_user, db_session):
    """display_name="" stays forbidden so an admin cannot strip a user's
    public handle. The endpoint surfaces it as a real HTTP 400."""
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
        "username": "grace",
        "password": "supersecret",
        "display_name": "Grace",
    })
    profile_id = resp.json()["profile_id"]

    resp = await client.patch(
        f"/api/portal/admin/users/{profile_id}",
        json={"display_name": "   "},
    )
    assert resp.status_code == 400
    assert resp.json().get("detail") == "display_name_empty"

    # Display name unchanged in DB.
    resp = await client.get(f"/api/portal/admin/users/{profile_id}")
    assert resp.json()["display_name"] == "Grace"


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
async def test_reset_display_name_flags_profile_and_audits(client, admin_user, db_session):
    """POST /reset-display-name must flip the must-set flag and log the action."""
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
        "username": "frank",
        "password": "supersecret",
        "display_name": "Frank",
    })
    assert resp.status_code == 200, resp.text
    profile_id = resp.json()["profile_id"]

    # Sanity: the freshly created user starts with the flag cleared
    # (admin-side identity update sets ``display_name_must_set=False``).
    resp = await client.get(f"/api/portal/admin/users/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["display_name_must_set"] is False

    # Reset
    resp = await client.post(
        f"/api/portal/admin/users/{profile_id}/reset-display-name"
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    # Flag now armed — the first-login overlay will reappear for the user
    resp = await client.get(f"/api/portal/admin/users/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["display_name_must_set"] is True

    # Audit log entry present
    resp = await client.get(f"/api/portal/admin/users/{profile_id}/audit")
    assert resp.status_code == 200
    actions = [item["action"] for item in resp.json()["items"]]
    assert "user.display_name_reset" in actions


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


async def _admin_profile(db_session, admin_user):
    """Create the admin's own profile; feeds resolve by its profile id."""
    profile = UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def _walk_cursor(client, url_base):
    """Walk a feed in pages of 2 via keyset cursor; return the collected ids."""
    seen: list[int] = []
    cursor = None
    for _ in range(10):  # safety bound well above the fixtures' row count
        url = f"{url_base}?limit=2" + (f"&cursor={cursor}" if cursor else "")
        resp = await client.get(url)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        seen.extend(item["id"] for item in data["items"])
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return seen


@pytest.mark.asyncio
async def test_user_requests_feed_cursor_pagination(client, admin_user, db_session):
    from models.portal.request import MediaRequest

    profile = await _admin_profile(db_session, admin_user)
    db_session.add_all([
        MediaRequest(user_id=admin_user.id, tmdb_id=7000 + i, media_type="movie",
                     title=f"Req {i:02d}", status="pending")
        for i in range(5)
    ])
    await db_session.commit()
    _auth(client, admin_user)

    seen = await _walk_cursor(client, f"/api/portal/admin/users/{profile.id}/requests")
    assert len(seen) == 5 and len(set(seen)) == 5


@pytest.mark.asyncio
async def test_user_tickets_feed_cursor_pagination(client, admin_user, db_session):
    from models.portal.ticket import Ticket

    profile = await _admin_profile(db_session, admin_user)
    db_session.add_all([
        Ticket(user_id=admin_user.id, media_title=f"Movie {i}", media_type="movie",
               issue_type="audio", description="x")
        for i in range(5)
    ])
    await db_session.commit()
    _auth(client, admin_user)

    seen = await _walk_cursor(client, f"/api/portal/admin/users/{profile.id}/tickets")
    assert len(seen) == 5 and len(set(seen)) == 5


@pytest.mark.asyncio
async def test_xp_history_feed_cursor_pagination(client, admin_user, db_session):
    from models.portal.xp_ledger import XpLedger

    profile = await _admin_profile(db_session, admin_user)
    db_session.add_all([
        XpLedger(user_id=admin_user.id, action="manual_grant", reference=f"ref-{i}", xp=10)
        for i in range(5)
    ])
    await db_session.commit()
    _auth(client, admin_user)

    seen = await _walk_cursor(client, f"/api/portal/admin/users/{profile.id}/xp-history")
    assert len(seen) == 5 and len(set(seen)) == 5


@pytest.mark.asyncio
async def test_login_history_feed_cursor_pagination(client, admin_user, db_session):
    from models.portal.login_history import UserLoginHistory

    profile = await _admin_profile(db_session, admin_user)
    db_session.add_all([
        UserLoginHistory(user_id=admin_user.id, source="portal", success=True)
        for _ in range(5)
    ])
    await db_session.commit()
    _auth(client, admin_user)

    seen = await _walk_cursor(client, f"/api/portal/admin/users/{profile.id}/login-history")
    assert len(seen) == 5 and len(set(seen)) == 5


@pytest.mark.asyncio
async def test_audit_feed_cursor_pagination(client, admin_user, db_session):
    from models.portal.audit import AdminAuditLog

    profile = await _admin_profile(db_session, admin_user)
    db_session.add_all([
        AdminAuditLog(admin_user_id=admin_user.id, target_user_id=admin_user.id,
                      action="test_action")
        for _ in range(5)
    ])
    await db_session.commit()
    _auth(client, admin_user)

    seen = await _walk_cursor(client, f"/api/portal/admin/users/{profile.id}/audit")
    assert len(seen) == 5 and len(set(seen)) == 5


@pytest.mark.asyncio
async def test_user_mutations_reject_unknown_field(client, admin_user, db_session):
    """extra="forbid" on the 5 user-mutation schemas: an unknown body field
    is rejected with 422 instead of being silently ignored. Validation fires
    before the handler, so any existing profile id exercises the contract."""
    profile = UserProfile(
        user_id=admin_user.id, display_name="Target", role="viewer",
        source="local", account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    _auth(client, admin_user)
    pid = profile.id
    cases = [
        (f"/api/portal/admin/users/{pid}", {"display_name": "X"}),
        (f"/api/portal/admin/users/{pid}/role", {"role": "moderator"}),
        (f"/api/portal/admin/users/{pid}/permissions", {"permissions": {"can_chat": True}}),
        (f"/api/portal/admin/users/{pid}/active", {"active": True}),
        (f"/api/portal/admin/users/{pid}/access", {"start": None, "end": None}),
    ]
    for url, body in cases:
        resp = await client.patch(url, json={**body, "unexpected": "x"})
        assert resp.status_code == 422, f"{url} -> {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_companion_mutations_reject_unknown_field(client, admin_user, db_session):
    """extra="forbid" on the companion (actions/emby) mutation schemas: an
    unknown body field is rejected with 422 instead of being silently ignored."""
    profile = UserProfile(
        user_id=admin_user.id, display_name="Target", role="viewer",
        source="local", account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    _auth(client, admin_user)
    pid = profile.id
    patch_cases = [
        (f"/api/portal/admin/users/{pid}/notes", {"notes": "x"}),
        (f"/api/portal/admin/users/{pid}/tags", {"tags": []}),
    ]
    post_cases = [
        (f"/api/portal/admin/users/{pid}/extend-access", {"months": 3}),
        (f"/api/portal/admin/users/{pid}/emby-toggle", {"enabled": True}),
        (f"/api/portal/admin/users/{pid}/notify", {"title": "t", "body": "b"}),
        ("/api/portal/admin/users/bulk", {"action": "activate", "profile_ids": [pid]}),
        ("/api/portal/admin/users/emby/import", {"emby_user_ids": ["x"]}),
        ("/api/portal/admin/users/local", {"username": "newcomer", "password": "supersecret"}),
    ]
    for url, body in patch_cases:
        resp = await client.patch(url, json={**body, "unexpected": "x"})
        assert resp.status_code == 422, f"{url} -> {resp.status_code}: {resp.text}"
    for url, body in post_cases:
        resp = await client.post(url, json={**body, "unexpected": "x"})
        assert resp.status_code == 422, f"{url} -> {resp.status_code}: {resp.text}"
