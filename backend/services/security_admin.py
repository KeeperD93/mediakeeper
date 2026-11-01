"""Admin-facing helpers for login security."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from constants.security import (
    BLOCK_REQUIRES_IP_OR_USERNAME,
    FAIL_WINDOW_SECONDS,
    TEMP_BLOCK_SECONDS,
)
from models.security import SecurityAttempt, SecurityBlock

# A block in force began at most TEMP_BLOCK_SECONDS ago, and the failures behind it
# are at most FAIL_WINDOW_SECONDS older than that.
_BLOCK_HISTORY = timedelta(seconds=TEMP_BLOCK_SECONDS + FAIL_WINDOW_SECONDS)


async def list_recent_attempts(
    db: AsyncSession,
    limit: int = 100,
    scope: str | None = None,
    only_failures: bool = False,
) -> list[dict]:
    stmt = select(SecurityAttempt).order_by(SecurityAttempt.created_at.desc()).limit(limit)
    if scope:
        stmt = stmt.where(SecurityAttempt.scope == scope)
    if only_failures:
        stmt = stmt.where(SecurityAttempt.success == 0)
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_attempt(r) for r in rows]


async def list_active_blocks(db: AsyncSession) -> list[dict]:
    active = or_(
        SecurityBlock.permanent == 1,
        SecurityBlock.blocked_until > datetime.now(timezone.utc),
    )
    stmt = select(SecurityBlock).where(active).order_by(SecurityBlock.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_block(r) for r in rows]


async def create_block(
    db: AsyncSession,
    *,
    admin_id: int | None,
    ip: str | None,
    username: str | None,
    scope: str,
    permanent: bool,
    blocked_until: datetime | None = None,
    reason: str | None = None,
) -> int:
    if not ip and not username:
        raise ValueError(BLOCK_REQUIRES_IP_OR_USERNAME)
    row = SecurityBlock(
        ip=ip or None,
        username=username or None,
        scope=scope,
        permanent=1 if permanent else 0,
        blocked_until=blocked_until,
        reason=reason,
        created_by=admin_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row.id


async def release_block(db: AsyncSession, block_id: int) -> dict | None:
    """Lift a block and say what went with it, or None when it no longer exists.

    An admin's own block only loses its row. Lifting an automatic one frees the
    person: its duplicates go too and the failures behind it stop counting, or the
    next typo would set it again. A name also frees the addresses it recently failed
    from, each able to refuse the person alone; every other name's failures from
    those addresses stop counting with them. An address keeps the name blocks: that
    account may be under attack.
    """
    row = await db.get(SecurityBlock, block_id)
    if row is None:
        return None
    released = [row]
    if row.automatic:
        released = await _release_automatic(db, row)
    summary = {
        "removed": [
            {"id": b.id, "ip": b.ip, "username": b.username, "scope": b.scope} for b in released
        ],
        "linked_addresses": len({b.ip for b in released if b.ip and b.ip != row.ip}),
    }
    await db.execute(
        delete(SecurityBlock)
        .where(SecurityBlock.id.in_([b.id for b in released]))
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()
    return summary


async def _release_automatic(db: AsyncSession, row: SecurityBlock) -> list[SecurityBlock]:
    """Neutralise the failures behind automatic block ``row``; return the blocks that go."""
    now = datetime.now(timezone.utc)
    # Up to now only: a failure arriving during the unblock was not behind this block.
    failures = (
        SecurityAttempt.success == 0,
        SecurityAttempt.scope == row.scope,
        SecurityAttempt.created_at >= now - _BLOCK_HISTORY,
        SecurityAttempt.created_at <= now,
    )
    if row.username:
        name = row.username.lower()
        by_name = func.lower(SecurityAttempt.username) == name
        same_target = or_(
            and_(SecurityBlock.ip.is_(None), func.lower(SecurityBlock.username) == name),
            and_(
                SecurityBlock.username.is_(None),
                # Already neutralised or not, the name did fail from there.
                SecurityBlock.ip.in_(select(SecurityAttempt.ip).where(*failures, by_name)),
            ),
        )
    else:
        by_name = None
        same_target = and_(SecurityBlock.username.is_(None), SecurityBlock.ip == row.ip)

    released = (await db.execute(
        select(SecurityBlock).where(or_(
            SecurityBlock.id == row.id,
            and_(
                same_target,
                SecurityBlock.automatic == 1,
                SecurityBlock.scope == row.scope,
                SecurityBlock.blocked_until > now,
            ),
        ))
    )).scalars().all()

    behind_block = SecurityAttempt.ip.in_([b.ip for b in released if b.ip])
    await db.execute(
        update(SecurityAttempt)
        .where(
            *failures,
            SecurityAttempt.cleared_at.is_(None),
            behind_block if by_name is None else or_(behind_block, by_name),
        )
        .values(cleared_at=now)
        .execution_options(synchronize_session="fetch")
    )
    return released


def _serialize_attempt(r: SecurityAttempt) -> dict:
    return {
        "id": r.id,
        "ip": r.ip,
        "username": r.username,
        "scope": r.scope,
        "success": bool(r.success),
        "user_agent": r.user_agent,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "cleared_at": r.cleared_at.isoformat() if r.cleared_at else None,
    }


def _serialize_block(r: SecurityBlock) -> dict:
    return {
        "id": r.id,
        "ip": r.ip,
        "username": r.username,
        "scope": r.scope,
        "permanent": bool(r.permanent),
        "automatic": bool(r.automatic),
        "blocked_until": r.blocked_until.isoformat() if r.blocked_until else None,
        "reason": r.reason,
        "created_by": r.created_by,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
