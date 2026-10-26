"""Automatic blocks carry their own marker: an admin's block is never taken for one."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.security import SecurityBlock
from services.security import FAIL_BLOCK_THRESHOLD, record_failure


@pytest.mark.asyncio
async def test_failed_sign_ins_set_marked_automatic_blocks(db_session):
    for _ in range(FAIL_BLOCK_THRESHOLD):
        await record_failure(db_session, "198.51.100.21", "member-a", "portal")

    blocks = (await db_session.execute(select(SecurityBlock))).scalars().all()
    assert len(blocks) == 2
    assert all(b.automatic == 1 and b.created_by is None for b in blocks)


@pytest.mark.asyncio
async def test_auto_block_leaves_an_admins_temporary_block_alone(db_session):
    """Its creator deleted, a manual block has no created_by left: it must keep
    its end and reason instead of being reused as an automatic block."""
    until = datetime.now(timezone.utc) + timedelta(hours=2)
    manual = SecurityBlock(
        username="member-b", scope="portal", permanent=0, blocked_until=until,
        reason="seen on the router", created_by=None,
    )
    db_session.add(manual)
    await db_session.commit()

    for _ in range(FAIL_BLOCK_THRESHOLD):
        await record_failure(db_session, "198.51.100.22", "member-b", "portal")

    await db_session.refresh(manual)
    assert manual.reason == "seen on the router"
    # SQLite hands the date back without its time zone.
    assert abs(manual.blocked_until.replace(tzinfo=timezone.utc) - until) < timedelta(seconds=1)
    assert manual.automatic == 0
    names = (await db_session.execute(
        select(SecurityBlock).where(SecurityBlock.username == "member-b", SecurityBlock.automatic == 1)
    )).scalars().all()
    assert len(names) == 1
    assert names[0].reason == "auto_block_bruteforce_username:portal"


@pytest.mark.asyncio
async def test_security_block_automatic_rejects_non_boolean(db_session):
    """The CHECK(0/1) guard refuses a marker outside the boolean range."""
    db_session.add(SecurityBlock(scope="admin", permanent=0, automatic=5))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
