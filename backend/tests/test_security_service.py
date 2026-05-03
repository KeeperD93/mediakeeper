"""Persistent login log + rate-limit + manual blocks."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import create_access_token, hash_password
from models.security import SecurityAttempt, SecurityBlock
from models.user import User
from services.security import (
    ALERT_THRESHOLD,
    FAIL_BLOCK_THRESHOLD,
    create_block,
    delete_block,
    ensure_not_blocked,
    is_blocked,
    purge_old_attempts,
    record_failure,
)


@pytest.mark.asyncio
async def test_record_failure_logs_row_and_auto_blocks_after_threshold(db_session):
    for _ in range(FAIL_BLOCK_THRESHOLD):
        await record_failure(db_session, "1.2.3.4", "victim", "admin")

    attempts = (
        await db_session.execute(select(SecurityAttempt).where(SecurityAttempt.ip == "1.2.3.4"))
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

    block = await is_blocked(db_session, "1.2.3.4", "victim", "admin")
    assert block is not None
    assert block.permanent == 0
    assert block.scope == "admin"
    assert block.reason.startswith("auto_block_bruteforce_")

    # Same IP, different scope → must not be blocked automatically.
    block_other = await is_blocked(db_session, "1.2.3.4", "victim", "portal")
    assert block_other is None


@pytest.mark.asyncio
async def test_alert_threshold_is_lower_or_equal_than_block_threshold():
    # Alert fires at or before the block kicks in.
    assert ALERT_THRESHOLD <= FAIL_BLOCK_THRESHOLD


@pytest.mark.asyncio
async def test_ensure_not_blocked_raises_429_when_blocked(db_session):
    await create_block(
        db_session,
        admin_id=None,
        ip="9.9.9.9",
        username=None,
        scope="admin",
        permanent=True,
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await ensure_not_blocked(db_session, "9.9.9.9", "anyone", "admin")
    assert excinfo.value.status_code == 429
    assert excinfo.value.detail == "login_blocked"


@pytest.mark.asyncio
async def test_ensure_not_blocked_passes_when_scope_differs(db_session):
    await create_block(
        db_session,
        admin_id=None,
        ip="8.8.8.8",
        username=None,
        scope="portal",
        permanent=True,
    )
    # Same IP but different scope → must pass.
    await ensure_not_blocked(db_session, "8.8.8.8", None, "admin")


@pytest.mark.asyncio
async def test_delete_block_removes_row(db_session):
    block_id = await create_block(
        db_session,
        admin_id=None,
        ip="7.7.7.7",
        username=None,
        scope="all",
        permanent=True,
    )
    assert await delete_block(db_session, block_id) is True
    assert await delete_block(db_session, block_id) is False


@pytest.mark.asyncio
async def test_purge_old_attempts_keeps_recent(db_session):
    recent = SecurityAttempt(
        ip="5.5.5.5", username="u", scope="admin", success=0,
        created_at=datetime.now(timezone.utc),
    )
    ancient = SecurityAttempt(
        ip="5.5.5.5", username="u", scope="admin", success=0,
        created_at=datetime.now(timezone.utc) - timedelta(days=100),
    )
    db_session.add_all([recent, ancient])
    await db_session.commit()

    deleted = await purge_old_attempts(db_session)
    assert deleted == 1

    remaining = (await db_session.execute(select(SecurityAttempt))).scalars().all()
    assert len(remaining) == 1


@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(client):
    resp = await client.get("/api/security/attempts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_list_and_manage_blocks(client, db_session):
    admin = User(
        username="admin",
        hashed_password=hash_password("TestPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    client.cookies.set("mk_token", create_access_token({"sub": admin.username, "scope": "admin"}))

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
async def test_login_endpoint_blocks_after_failures(client, db_session):
    # Prime: create admin user so the /login path exercises the real failure flow
    admin = User(
        username="admin",
        hashed_password=hash_password("GoodPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(admin)
    await db_session.commit()

    for _ in range(FAIL_BLOCK_THRESHOLD):
        await client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong-password"
        })

    # The next attempt (even with the correct password) is blocked.
    resp = await client.post("/api/auth/login", json={
        "username": "admin", "password": "GoodPassword123!"
    })
    assert resp.status_code == 429
    assert resp.json()["detail"] == "login_blocked"
