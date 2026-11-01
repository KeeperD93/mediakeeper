"""Persistent login log + rate-limit + manual blocks."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from models.security import SecurityAttempt, SecurityBlock
from models.user import User
from services.security import (
    ALERT_THRESHOLD,
    FAIL_BLOCK_THRESHOLD,
    RETENTION_DAYS,
    active_blocks,
    create_block,
    ensure_not_blocked,
    purge_old_attempts,
    record_failure,
    release_block,
)


def _auth_admin(client: AsyncClient, admin_user: User) -> None:
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


async def _block_ip(db_session: AsyncSession, ip: str, scope: str) -> int:
    return await create_block(
        db_session, admin_id=None, ip=ip, username=None, scope=scope, permanent=True,
    )


@pytest.mark.asyncio
async def test_record_failure_logs_row_and_auto_blocks_after_threshold(db_session):
    for _ in range(FAIL_BLOCK_THRESHOLD):
        await record_failure(db_session, "198.51.100.4", "victim", "admin")

    attempts = (
        await db_session.execute(select(SecurityAttempt).where(SecurityAttempt.ip == "198.51.100.4"))
    ).scalars().all()
    assert len(attempts) == FAIL_BLOCK_THRESHOLD
    assert all(a.success == 0 for a in attempts)

    blocks = (
        await db_session.execute(
            select(SecurityBlock).where(SecurityBlock.scope == "admin")
        )
    ).scalars().all()
    assert len(blocks) == 2
    assert {block.reason for block in blocks} == {
        "auto_block_bruteforce_ip:admin",
        "auto_block_bruteforce_username:admin",
    }

    refusing = await active_blocks(db_session, "198.51.100.4", "victim", "admin")
    assert {b.id for b in refusing} == {b.id for b in blocks}
    assert all(b.permanent == 0 for b in refusing)

    # Same IP, different scope → must not be blocked automatically.
    assert await active_blocks(db_session, "198.51.100.4", "victim", "portal") == []


def test_alert_threshold_is_at_most_the_block_threshold():
    # Alert fires at or before the block kicks in.
    assert ALERT_THRESHOLD <= FAIL_BLOCK_THRESHOLD


@pytest.mark.asyncio
async def test_ensure_not_blocked_raises_429_when_blocked(db_session):
    await _block_ip(db_session, "198.51.100.9", "admin")
    with pytest.raises(HTTPException) as excinfo:
        await ensure_not_blocked(db_session, "198.51.100.9", "anyone", "admin")
    assert excinfo.value.status_code == 429
    assert excinfo.value.detail == "login_blocked"


@pytest.mark.asyncio
async def test_security_attempt_success_rejects_non_boolean(db_session):
    """The CHECK(0/1) guard refuses a success value outside the boolean range."""
    db_session.add(SecurityAttempt(ip="198.51.100.2", scope="admin", success=2))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_security_block_permanent_rejects_non_boolean(db_session):
    """The CHECK(0/1) guard refuses a permanent value outside the boolean range."""
    db_session.add(SecurityBlock(scope="admin", permanent=5))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_ensure_not_blocked_passes_when_scope_differs(db_session):
    await _block_ip(db_session, "198.51.100.8", "portal")
    # Same IP but different scope → must pass.
    await ensure_not_blocked(db_session, "198.51.100.8", None, "admin")


@pytest.mark.asyncio
async def test_release_block_removes_row(db_session):
    block_id = await _block_ip(db_session, "198.51.100.7", "all")
    assert (await release_block(db_session, block_id))["removed"] == [
        {"id": block_id, "ip": "198.51.100.7", "username": None, "scope": "all"},
    ]
    assert await release_block(db_session, block_id) is None


@pytest.mark.asyncio
async def test_purge_old_attempts_drops_only_rows_past_retention(db_session):
    now = datetime.now(timezone.utc)
    ages = {"recent": 0, "inside": RETENTION_DAYS - 1, "ancient": RETENTION_DAYS + 1}
    db_session.add_all([
        SecurityAttempt(
            ip="198.51.100.5", username=name, scope="admin", success=0,
            created_at=now - timedelta(days=days),
        )
        for name, days in ages.items()
    ])
    await db_session.commit()

    assert await purge_old_attempts(db_session) == 1

    remaining = (await db_session.execute(select(SecurityAttempt.username))).scalars().all()
    assert sorted(remaining) == ["inside", "recent"]


@pytest.mark.parametrize("method, path", [
    ("GET", "/api/security/attempts"),
    ("GET", "/api/security/blocks"),
    ("POST", "/api/security/blocks"),
    ("DELETE", "/api/security/blocks/1"),
    ("POST", "/api/security/attempts/purge"),
])
@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(client, method, path):
    body = {"ip": "198.51.100.1", "scope": "all"} if method == "POST" else None
    resp = await client.request(method, path, json=body)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_list_and_manage_blocks(client, admin_user):
    _auth_admin(client, admin_user)

    resp = await client.post("/api/security/blocks", json={
        "ip": "10.0.0.1",
        "scope": "admin",
        "permanent": True,
        "reason": "manual",
    })
    assert resp.status_code == 200
    block_id = resp.json()["id"]

    listing = await client.get("/api/security/blocks")
    assert listing.status_code == 200
    assert any(b["id"] == block_id for b in listing.json()["items"])

    delete_resp = await client.delete(f"/api/security/blocks/{block_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_post_block_rejects_inert_non_permanent_block(client, admin_user):
    """A non-permanent block with no future expiry is inert (never active,
    hidden from the list); the API must reject it (400) instead of silently
    storing a dead row."""
    _auth_admin(client, admin_user)

    no_expiry = await client.post("/api/security/blocks", json={
        "ip": "203.0.113.5", "scope": "all", "permanent": False,
    })
    assert no_expiry.status_code == 400
    assert no_expiry.json()["detail"] == "block_requires_future_expiry"

    past = await client.post("/api/security/blocks", json={
        "ip": "203.0.113.5", "scope": "all", "permanent": False,
        "blocked_until": "2000-01-01T00:00:00+00:00",
    })
    assert past.status_code == 400
    assert past.json()["detail"] == "block_requires_future_expiry"

    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    ok = await client.post("/api/security/blocks", json={
        "ip": "203.0.113.5", "scope": "all", "permanent": False,
        "blocked_until": future,
    })
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_post_block_refuses_self_block_by_username(client, admin_user):
    """Blocking the operator's own username would lock them out of the
    backoffice after JWT expiry; the API must refuse it."""
    _auth_admin(client, admin_user)

    own = await client.post("/api/security/blocks", json={
        "username": admin_user.username, "scope": "all", "permanent": True,
    })
    assert own.status_code == 400
    assert own.json()["detail"] == "self_block_forbidden"

    other = await client.post("/api/security/blocks", json={
        "username": "someone-else", "scope": "all", "permanent": True,
    })
    assert other.status_code == 200


@pytest.mark.asyncio
async def test_post_block_stores_the_ip_in_canonical_form(client, admin_user, db_session):
    """Blocks are matched against normalized client IPs: another spelling of
    the same address must still match, including the operator's own one."""
    _auth_admin(client, admin_user)

    own = await client.post("/api/security/blocks", json={
        "ip": "::ffff:127.0.0.1", "scope": "all", "permanent": True,
    })
    assert own.status_code == 400
    assert own.json()["detail"] == "self_block_forbidden"

    ok = await client.post("/api/security/blocks", json={
        "ip": "2001:DB8:0:0:0:0:0:1", "scope": "all", "permanent": True,
    })
    assert ok.status_code == 200
    assert await active_blocks(db_session, "2001:db8::1", None, "admin")


@pytest.mark.asyncio
async def test_post_block_accepts_the_unknown_marker(client, admin_user, db_session):
    """An operator whose own address is readable may block the marker by hand:
    it matches the sign-ins recorded under it."""
    _auth_admin(client, admin_user)

    resp = await client.post("/api/security/blocks", json={
        "ip": "unknown", "scope": "admin", "permanent": True,
    })
    assert resp.status_code == 200
    assert await active_blocks(db_session, "unknown", None, "admin")


@pytest.mark.asyncio
async def test_login_endpoint_blocks_after_failures(client, admin_user):
    # A real account, so the last attempt can use the correct password.
    for _ in range(FAIL_BLOCK_THRESHOLD):
        await client.post("/api/auth/login", json={
            "username": admin_user.username, "password": "wrong-password"
        })

    # The next attempt (even with the correct password) is blocked.
    resp = await client.post("/api/auth/login", json={
        "username": admin_user.username, "password": "TestPassword123!"
    })
    assert resp.status_code == 429
    assert resp.json()["detail"] == "login_blocked"
