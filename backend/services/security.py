"""Security service: login attempts log, rate-limit, manual blocks, alerts.

Replaces the in-memory ``_login_attempts`` dict. Every login attempt (success
or failure) is persisted so an admin can audit abuse, manually unban or
permanently block an IP or username.

Thresholds:
  - ``FAIL_BLOCK_THRESHOLD`` (5) failed attempts within ``FAIL_WINDOW_SECONDS``
    (5 min) → automatic temporary block for ``TEMP_BLOCK_SECONDS`` (10 min).
  - ``ALERT_THRESHOLD`` (3) failed attempts in the same window → fire an
    admin alert via the notification engine (best-effort, never fatal).

Retention: ``RETENTION_DAYS`` (90). Purged by the scheduler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.security import SecurityAttempt, SecurityBlock
from services.security_admin import (
    create_block as create_block,
    delete_block as delete_block,
    list_active_blocks as list_active_blocks,
    list_recent_attempts as list_recent_attempts,
)

logger = logging.getLogger("mediakeeper.security")

FAIL_BLOCK_THRESHOLD = 3
ALERT_THRESHOLD = 3
FAIL_WINDOW_SECONDS = 300
TEMP_BLOCK_SECONDS = 600
RETENTION_DAYS = 90
ALERT_COOLDOWN_SECONDS = 600  # don't re-alert the same IP/user more often


async def count_recent_failures(
    db: AsyncSession,
    ip: str,
    username: str | None,
    scope: str,
    within_seconds: int = FAIL_WINDOW_SECONDS,
) -> int:
    """Return the username-specific counter when available, otherwise the IP counter."""
    username_failures = await _count_recent_username_failures(
        db, username, scope, within_seconds,
    )
    if username and username_failures:
        return username_failures
    return await _count_recent_ip_failures(db, ip, scope, within_seconds)


async def _count_recent_ip_failures(
    db: AsyncSession, ip: str, scope: str, within_seconds: int,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
    stmt = select(SecurityAttempt).where(
        and_(
            SecurityAttempt.success == 0,
            SecurityAttempt.scope == scope,
            SecurityAttempt.created_at >= cutoff,
            SecurityAttempt.ip == ip,
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    return len(rows)


async def _count_recent_username_failures(
    db: AsyncSession, username: str | None, scope: str, within_seconds: int,
) -> int:
    if not username:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
    stmt = select(SecurityAttempt).where(
        and_(
            SecurityAttempt.success == 0,
            SecurityAttempt.scope == scope,
            SecurityAttempt.created_at >= cutoff,
            SecurityAttempt.username == username,
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    return len(rows)


async def is_blocked(
    db: AsyncSession, ip: str, username: str | None, scope: str
) -> SecurityBlock | None:
    """Return the matching block row if the caller is currently blocked."""
    now = datetime.now(timezone.utc)
    conditions = [SecurityBlock.scope.in_([scope, "all"])]
    ip_or_user = [SecurityBlock.ip == ip]
    if username:
        ip_or_user.append(SecurityBlock.username == username)
    conditions.append(or_(*ip_or_user))
    active = or_(
        SecurityBlock.permanent == 1,
        SecurityBlock.blocked_until > now,
    )
    stmt = select(SecurityBlock).where(and_(*conditions, active))
    return (await db.execute(stmt)).scalars().first()


async def ensure_not_blocked(
    db: AsyncSession, ip: str, username: str | None, scope: str
) -> None:
    """Raise 429 if the caller is currently blocked. Call before auth."""
    block = await is_blocked(db, ip, username, scope)
    if block is None:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="login_blocked",
    )


async def record_attempt(
    db: AsyncSession,
    ip: str,
    username: str | None,
    scope: str,
    success: bool,
    user_agent: str | None = None,
) -> None:
    """Persist an attempt row. Failures may trigger auto-block / alert below."""
    db.add(SecurityAttempt(
        ip=ip,
        username=username,
        scope=scope,
        success=1 if success else 0,
        user_agent=(user_agent or "")[:300] or None,
    ))
    await db.commit()


async def _auto_block(
    db: AsyncSession,
    *,
    ip: str | None,
    username: str | None,
    scope: str,
    reason_suffix: str,
) -> None:
    """Auto-block after ``FAIL_BLOCK_THRESHOLD`` failures on one identity."""
    until = datetime.now(timezone.utc) + timedelta(seconds=TEMP_BLOCK_SECONDS)
    filters = [
        SecurityBlock.scope == scope,
        SecurityBlock.permanent == 0,
        SecurityBlock.created_by.is_(None),
        SecurityBlock.ip.is_(ip) if ip is None else SecurityBlock.ip == ip,
        SecurityBlock.username.is_(username) if username is None else SecurityBlock.username == username,
    ]
    existing = (await db.execute(
        select(SecurityBlock).where(and_(*filters))
    )).scalars().first()
    if existing:
        existing.blocked_until = until
        existing.username = username
        existing.ip = ip
        existing.reason = f"auto_block_bruteforce_{reason_suffix}:{scope}"
        db.add(existing)
    else:
        db.add(SecurityBlock(
            ip=ip,
            username=username,
            scope=scope,
            permanent=0,
            blocked_until=until,
            reason=f"auto_block_bruteforce_{reason_suffix}:{scope}",
        ))
    await db.commit()
    logger.warning(
        "[SECURITY] auto-block scope=%s ip=%s user=%s reason=%s",
        scope,
        ip,
        username,
        reason_suffix,
    )


async def _maybe_alert(
    db: AsyncSession,
    ip: str,
    username: str | None,
    scope: str,
    ip_failures: int,
    username_failures: int,
) -> None:
    """Log a structured warning when ``ALERT_THRESHOLD`` is reached.

    The dashboard reads the attempts table directly; this line also lets
    any external log pipeline (Discord webhook, Grafana) pick up the event.
    """
    if ip_failures < ALERT_THRESHOLD and username_failures < ALERT_THRESHOLD:
        return
    if ip_failures != ALERT_THRESHOLD and username_failures != ALERT_THRESHOLD:
        return
    logger.warning(
        "[SECURITY_ALERT] scope=%s ip=%s ip_failures=%d user=%s user_failures=%d",
        scope,
        ip,
        ip_failures,
        username or "-",
        username_failures,
    )


async def record_failure(
    db: AsyncSession,
    ip: str,
    username: str | None,
    scope: str,
    user_agent: str | None = None,
) -> None:
    """Log a failed attempt, then decide whether to alert or auto-block."""
    await record_attempt(db, ip, username, scope, success=False, user_agent=user_agent)
    ip_failures = await _count_recent_ip_failures(db, ip, scope, FAIL_WINDOW_SECONDS)
    username_failures = await _count_recent_username_failures(
        db, username, scope, FAIL_WINDOW_SECONDS,
    )
    if ip_failures >= FAIL_BLOCK_THRESHOLD:
        await _auto_block(
            db,
            ip=ip,
            username=None,
            scope=scope,
            reason_suffix="ip",
        )
    if username and username_failures >= FAIL_BLOCK_THRESHOLD:
        await _auto_block(
            db,
            ip=None,
            username=username,
            scope=scope,
            reason_suffix="username",
        )
    await _maybe_alert(db, ip, username, scope, ip_failures, username_failures)


async def purge_old_attempts(db: AsyncSession) -> int:
    """Called by the scheduler. Drops rows older than ``RETENTION_DAYS``."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    result = await db.execute(
        delete(SecurityAttempt).where(SecurityAttempt.created_at < cutoff)
    )
    await db.commit()
    return result.rowcount or 0
