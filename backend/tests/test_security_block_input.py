"""Security dashboard input: manual-block names and addresses, the block schema's guards,
unblocking and the attempts filter."""
import pytest

from core.security import hash_password
from models.user import User
from services.security import active_blocks, create_block


@pytest.mark.asyncio
async def test_username_blocks_apply_whatever_the_case(authed_client, db_session):
    """Sign-ins are matched with the lower-cased name: a block typed with capitals
    must still apply, and so must rows stored before names were normalized."""
    resp = await authed_client.post("/api/security/blocks", json={
        "username": " Alice ", "scope": "all", "permanent": True,
    })
    assert resp.status_code == 200
    blocks = (await authed_client.get("/api/security/blocks")).json()["items"]
    assert [b["username"] for b in blocks] == ["alice"]
    login = await authed_client.post("/api/auth/login", json={"username": "ALICE", "password": "wrong"})
    assert login.status_code == 429
    assert login.json()["detail"] == "login_blocked"

    await create_block(db_session, admin_id=None, ip=None, username="Bob", scope="all", permanent=True)
    for name in ("bob", "BOB"):
        assert await active_blocks(db_session, "198.51.100.3", name, "admin")


@pytest.mark.asyncio
async def test_self_block_is_refused_whatever_the_case(client, db_session, monkeypatch):
    """Both sides are compared lower-cased: the typed name and the admin's stored name."""
    monkeypatch.setenv("MK_ADMIN_USERS", "AdminUser")
    db_session.add(User(
        username="AdminUser",
        hashed_password=hash_password("TestPassword123!"),
        is_active=True,
        must_change_password=False,
    ))
    await db_session.commit()
    login = await client.post("/api/auth/login", json={"username": "adminuser", "password": "TestPassword123!"})
    assert login.status_code == 200, login.text

    resp = await client.post("/api/security/blocks", json={"username": " ADMINUSER ", "scope": "all"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "self_block_forbidden"


@pytest.mark.parametrize("body, expected", [
    ({"scope": "all"}, "block_requires_ip_or_username"),
    ({"ip": "", "username": "  ", "scope": "all"}, "block_requires_ip_or_username"),
    ({"ip": "203.0.113.9", "scope": "bogus"}, "invalid_scope"),
    # Lower-casing turns each "İ" into two characters: the limit applies to the stored form.
    ({"username": "İ" * 60, "scope": "all"}, "at most 100 characters"),
])
@pytest.mark.asyncio
async def test_post_block_schema_rejects_bad_input(authed_client, body, expected):
    """The request schema is the only guard in front of create_block."""
    resp = await authed_client.post("/api/security/blocks", json=body)
    assert resp.status_code == 422
    assert expected in resp.json()["detail"][0]["msg"]


@pytest.mark.parametrize("raw", ["203.0.113.0/24", "203.0.113", "not-an-address", "unknown-host"])
@pytest.mark.asyncio
async def test_post_block_refuses_a_value_that_is_not_an_address(authed_client, raw):
    """A range or a typo would be listed as active and never match a sign-in."""
    resp = await authed_client.post("/api/security/blocks", json={"ip": raw, "scope": "all"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_ip"
    assert (await authed_client.get("/api/security/blocks")).json()["items"] == []


@pytest.mark.asyncio
async def test_post_block_stores_the_unknown_marker_lower_cased(authed_client, db_session):
    resp = await authed_client.post("/api/security/blocks", json={"ip": " Unknown ", "scope": "admin"})
    assert resp.status_code == 200
    assert await active_blocks(db_session, "unknown", None, "admin")


@pytest.mark.asyncio
async def test_unknown_marker_is_a_self_block_when_the_operator_ip_is_unreadable(authed_client, monkeypatch):
    """Such an operator signs in under the marker: blocking it would lock them out."""
    monkeypatch.setattr("api.security.get_client_ip", lambda request: None)
    resp = await authed_client.post("/api/security/blocks", json={"ip": "unknown", "scope": "all"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "self_block_forbidden"


@pytest.mark.asyncio
async def test_unblocking_a_block_already_removed_says_block_not_found(authed_client):
    """The Security tab treats this code as an unblock already done elsewhere."""
    resp = await authed_client.delete("/api/security/blocks/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "block_not_found"


@pytest.mark.asyncio
async def test_attempts_filter_rejects_an_unknown_scope(authed_client):
    resp = await authed_client.get("/api/security/attempts", params={"scope": "bogus"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_scope"
