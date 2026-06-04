"""Username lock + auto-resolve + check-username endpoint coverage.

Avatar upload and public profile lookup live in
``test_portal_avatar_upload.py`` and ``test_portal_public_profile.py``.
"""
from __future__ import annotations

import pytest

from services.portal.profiles import (
    DISPLAY_NAME_LOCK_DAYS,
    is_display_name_locked,
    resolve_unique_display_name,
)
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


# ─────────────────────────────────────────────────────────────────────────
# Service layer
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_unique_display_name_appends_suffix(db_session):
    await make_portal_user(db_session, username="alice", display_name="alice")
    await make_portal_user(db_session, username="bob", display_name="alice2")
    assert await resolve_unique_display_name(db_session, "alice") == "alice3"


@pytest.mark.asyncio
async def test_resolve_unique_display_name_case_insensitive(db_session):
    await make_portal_user(db_session, username="alice", display_name="Alice")
    assert await resolve_unique_display_name(db_session, "ALICE") == "ALICE2"


@pytest.mark.asyncio
async def test_resolve_unique_excludes_current_user(db_session):
    user, _ = await make_portal_user(db_session, username="alice", display_name="Alice")
    resolved = await resolve_unique_display_name(
        db_session, "alice", exclude_user_id=user.id,
    )
    assert resolved == "alice"


@pytest.mark.asyncio
async def test_is_display_name_locked_inside_window(db_session):
    _, profile = await make_portal_user(
        db_session, username="alice", changed_days_ago=10,
    )
    assert is_display_name_locked(profile) is True


@pytest.mark.asyncio
async def test_is_display_name_locked_after_window(db_session):
    _, profile = await make_portal_user(
        db_session, username="alice", changed_days_ago=DISPLAY_NAME_LOCK_DAYS + 1,
    )
    assert is_display_name_locked(profile) is False


@pytest.mark.asyncio
async def test_is_display_name_locked_when_must_set(db_session):
    _, profile = await make_portal_user(
        db_session, username="alice", must_set=True, changed_days_ago=1,
    )
    assert is_display_name_locked(profile) is False


# ─────────────────────────────────────────────────────────────────────────
# PUT /me — first set, lock, auto-resolve
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_me_first_set_clears_must_set(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="alice", must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.put("/api/portal/profiles/me", json={"display_name": "Cinephile42"})
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["display_name"] == "Cinephile42"
    assert body["display_name_must_set"] is False
    assert body["display_name_changed_at"] is not None


@pytest.mark.asyncio
async def test_put_me_rejects_change_within_lock(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice", changed_days_ago=10,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.put("/api/portal/profiles/me", json={"display_name": "Alice2"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "display_name_locked"


@pytest.mark.asyncio
async def test_put_me_rejects_collision_with_409(client, db_session):
    await make_portal_user(db_session, username="bob", display_name="Taken")
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="alice", must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.put("/api/portal/profiles/me", json={"display_name": "taken"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_taken"


@pytest.mark.asyncio
async def test_put_me_same_name_clears_must_set_on_first_login(client, db_session):
    """A user who validates the modal with their current (auto-imported)
    Emby username must have ``must_set`` cleared too — otherwise the
    blocking modal reappears on the next login forever."""
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="alice", must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.put("/api/portal/profiles/me", json={"display_name": "alice"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name_must_set"] is False
    assert body["display_name_changed_at"] is not None


@pytest.mark.asyncio
async def test_put_me_same_display_name_does_not_relock(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice",
        changed_days_ago=DISPLAY_NAME_LOCK_DAYS + 5,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.put("/api/portal/profiles/me", json={"bio": "hello"})
    assert resp.status_code == 200
    assert resp.json()["bio"] == "hello"


# ─────────────────────────────────────────────────────────────────────────
# /me/check-username
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_username_free(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice", must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.get(
        "/api/portal/profiles/me/check-username", params={"name": "Brand_New"},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["available"] is True
    assert body["reason"] == "free"


@pytest.mark.asyncio
async def test_check_username_taken_case_insensitive(client, db_session):
    await make_portal_user(db_session, username="bob", display_name="Cinephile")
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice", must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.get(
        "/api/portal/profiles/me/check-username", params={"name": "cinephile"},
    )
    body = resp.json()
    assert body["available"] is False
    assert body["reason"] == "taken"
    assert body["suggestions"], "should suggest free variants"
    assert all(s.lower().startswith("cinephile") for s in body["suggestions"])
    assert "cinephile2" in [s.lower() for s in body["suggestions"]]


@pytest.mark.asyncio
async def test_check_username_locked(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice", changed_days_ago=10,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.get(
        "/api/portal/profiles/me/check-username", params={"name": "NewName"},
    )
    body = resp.json()
    assert body["available"] is False
    assert body["reason"] == "locked"
    assert body["locked_until"] is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["admin", "Admin", "ADMIN", "administrateur", "ROOT"])
async def test_check_username_reserved(client, db_session, name):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice", must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.get(
        "/api/portal/profiles/me/check-username", params={"name": name},
    )
    body = resp.json()
    assert body["available"] is False
    assert body["reason"] == "reserved"


@pytest.mark.asyncio
async def test_put_me_rejects_reserved_name(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice", must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.put("/api/portal/profiles/me", json={"display_name": "root"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_reserved"


@pytest.mark.asyncio
async def test_put_me_rejects_unknown_field(client, db_session):
    # ProfileUpdate uses extra="forbid": an unknown key is a 422, not silently dropped.
    user, _ = await make_portal_user(db_session, username="ulrich", display_name="Ulrich")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    resp = await client.put("/api/portal/profiles/me", json={"bogus_field": "x"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_can_keep_admin_username(client, db_session):
    admin, _ = await make_portal_user(
        db_session, username="admin", display_name="admin", role="admin",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    resp = await client.put("/api/portal/profiles/me", json={"bio": "hi"})
    assert resp.status_code == 200
    assert resp.json()["bio"] == "hi"


@pytest.mark.asyncio
async def test_admin_serializer_clears_must_set(client, db_session):
    admin, _ = await make_portal_user(
        db_session, username="admin", display_name="admin", role="admin",
        must_set=True,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    resp = await client.get("/api/portal/profiles/me")
    body = resp.json()
    assert body["display_name_must_set"] is False


@pytest.mark.asyncio
async def test_check_username_current_returns_available(client, db_session):
    user, _ = await make_portal_user(
        db_session, username="alice", display_name="Alice", changed_days_ago=10,
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.get(
        "/api/portal/profiles/me/check-username", params={"name": "alice"},
    )
    body = resp.json()
    assert body["available"] is True
    assert body["reason"] == "current"
