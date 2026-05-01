"""Admin-facing helpers for login security."""
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.security import SecurityAttempt, SecurityBlock


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
    admin_id: int,
    ip: str | None,
    username: str | None,
    scope: str,
    permanent: bool,
    blocked_until: datetime | None = None,
    reason: str | None = None,
) -> int:
    if not ip and not username:
        raise ValueError("block_requires_ip_or_username")
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


async def delete_block(db: AsyncSession, block_id: int) -> bool:
    row = await db.get(SecurityBlock, block_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True


def _serialize_attempt(r: SecurityAttempt) -> dict:
    return {
        "id": r.id,
        "ip": r.ip,
        "username": r.username,
        "scope": r.scope,
        "success": bool(r.success),
        "user_agent": r.user_agent,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_block(r: SecurityBlock) -> dict:
    return {
        "id": r.id,
        "ip": r.ip,
        "username": r.username,
        "scope": r.scope,
        "permanent": bool(r.permanent),
        "blocked_until": r.blocked_until.isoformat() if r.blocked_until else None,
        "reason": r.reason,
        "created_by": r.created_by,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
