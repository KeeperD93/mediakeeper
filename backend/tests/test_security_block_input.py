"""Manual blocks: username normalization and the request schema's guards."""
import pytest

from services.security import create_block, is_blocked


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
        assert await is_blocked(db_session, "198.51.100.3", name, "admin")


@pytest.mark.parametrize("body, code", [
    ({"scope": "all"}, "block_requires_ip_or_username"),
    ({"ip": "", "username": "  ", "scope": "all"}, "block_requires_ip_or_username"),
    ({"ip": "203.0.113.9", "scope": "bogus"}, "invalid_scope"),
])
@pytest.mark.asyncio
async def test_post_block_schema_rejects_bad_input(authed_client, body, code):
    """The request schema is the only guard in front of create_block."""
    resp = await authed_client.post("/api/security/blocks", json=body)
    assert resp.status_code == 422
    assert code in resp.json()["detail"][0]["msg"]


@pytest.mark.asyncio
async def test_attempts_filter_rejects_an_unknown_scope(authed_client):
    resp = await authed_client.get("/api/security/attempts", params={"scope": "bogus"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_scope"
