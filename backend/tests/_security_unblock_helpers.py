"""Attempts and blocks set up directly, and what is left of them after an unblock."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from models.security import SecurityAttempt, SecurityBlock
from services.security import FAIL_BLOCK_THRESHOLD, record_failure

HOME = "198.51.100.31"
AWAY = "198.51.100.32"
OTHER = "198.51.100.33"


async def fail(db, ip: str, name: str, *, scope: str = "portal", times: int = FAIL_BLOCK_THRESHOLD) -> None:
    for _ in range(times):
        await record_failure(db, ip, name, scope)


async def add_attempt(db, ip: str, name: str, *, age: int = 0, cleared: bool = False, success: int = 0) -> None:
    """A logged attempt ``age`` seconds old (negative: still to come)."""
    now = datetime.now(timezone.utc)
    db.add(SecurityAttempt(
        ip=ip, username=name, scope="portal", success=success,
        created_at=now - timedelta(seconds=age),
        cleared_at=now - timedelta(seconds=60) if cleared else None,
    ))
    await db.commit()


async def add_block(db, *, ip: str | None = None, username: str | None = None, scope: str = "portal",
                    automatic: int = 1, ends_in: int = 600) -> int:
    row = SecurityBlock(
        ip=ip, username=username, scope=scope, permanent=0, automatic=automatic,
        blocked_until=datetime.now(timezone.utc) + timedelta(seconds=ends_in),
    )
    db.add(row)
    await db.commit()
    return row.id


async def find_block(db, *, ip: str | None = None, username: str | None = None, scope: str = "portal") -> int:
    return (await db.execute(
        select(SecurityBlock.id).where(
            SecurityBlock.ip.is_(ip) if ip is None else SecurityBlock.ip == ip,
            SecurityBlock.username.is_(username) if username is None else SecurityBlock.username == username,
            SecurityBlock.scope == scope,
        )
    )).scalars().one()


async def remaining_blocks(db) -> set[tuple]:
    rows = await db.execute(select(SecurityBlock.ip, SecurityBlock.username, SecurityBlock.scope))
    return {tuple(row) for row in rows}


async def still_counting(db) -> list[tuple]:
    """The attempts no unblock or success has neutralised, in the order they were logged."""
    rows = await db.execute(
        select(SecurityAttempt.ip, SecurityAttempt.username)
        .where(SecurityAttempt.cleared_at.is_(None)).order_by(SecurityAttempt.id)
    )
    return [tuple(row) for row in rows]
