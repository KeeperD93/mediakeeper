"""Quota management for media requests.

Each user has a monthly quota row (``RequestQuota``) — created lazily on
first request, reset to ``used = 0`` whenever the calendar month changes.
``unlimited = True`` skips the cap entirely. Admin accounts bypass the
quota at the route layer (``is_admin`` flag in :func:`create_request`),
so the DB row is left untouched for them.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.request import RequestQuota


def current_month() -> str:
    """Current calendar month as ``YYYY-MM`` (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def _load_quota(
    db: AsyncSession,
    user_id: int,
    *,
    lock_row: bool = False,
) -> RequestQuota | None:
    """SELECT the user's quota row, optionally with ``FOR UPDATE``.

    Extracted so the lazy-create path in :func:`get_or_create_quota` can
    reload the winning row after a unique-constraint conflict — and so
    tests can monkeypatch this single seam to force the INSERT branch.
    """
    stmt = select(RequestQuota).where(RequestQuota.user_id == user_id)
    if lock_row:
        bind = db.get_bind()
        if bind is not None and bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_quota(
    db: AsyncSession,
    user_id: int,
    *,
    commit: bool = True,
    lock_row: bool = False,
) -> RequestQuota:
    """Return the user's quota row, creating it on first access.

    ``commit=False`` lets the caller batch the insert with another
    transaction (e.g. inside ``create_request`` where the quota update
    is part of the same write).

    ``lock_row=True`` adds ``FOR UPDATE`` on the SELECT so concurrent
    request creations serialize on the quota row — prevents check-then-
    increment races that let a user slip past ``max_allowed`` with
    rapid-fire clicks. The flag is ignored on SQLite (tests).

    Concurrent first-access is absorbed by a SAVEPOINT around the
    INSERT: if a parallel call wins the ``user_id`` unique race, the
    nested rollback keeps the caller's session usable and we reload
    the winning row instead of leaking the ``IntegrityError``.
    """
    quota = await _load_quota(db, user_id, lock_row=lock_row)
    if quota is not None:
        return quota

    new_quota = RequestQuota(user_id=user_id, month=current_month())
    try:
        async with db.begin_nested():
            db.add(new_quota)
            await db.flush()
        quota = new_quota
    except IntegrityError:
        quota = await _load_quota(db, user_id, lock_row=lock_row)
        if quota is None:
            raise
    if commit:
        await db.commit()
        await db.refresh(quota)
    return quota


async def get_user_quota(db: AsyncSession, user_id: int) -> dict:
    """Public quota snapshot — used by ``GET /api/portal/requests/quota``.

    Resets ``used`` to 0 when the stored month is stale before returning
    the snapshot, so the frontend never sees last month's leftover.
    """
    quota = await get_or_create_quota(db, user_id)
    month_now = current_month()
    if quota.month != month_now:
        quota.month = month_now
        quota.used = 0
        db.add(quota)
        await db.commit()
    return {
        "used": quota.used,
        "max_allowed": quota.max_allowed,
        "unlimited": quota.unlimited,
        "auto_approve": quota.auto_approve,
        "mode": quota.mode,
        "month": quota.month,
        "auto_min": quota.auto_min,
        "auto_max": quota.auto_max,
        "last_recomputed_at": (
            quota.last_recomputed_at.isoformat() if quota.last_recomputed_at else None
        ),
    }
