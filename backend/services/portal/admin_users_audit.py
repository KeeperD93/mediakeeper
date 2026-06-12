"""Admin audit log helpers.

Every mutation routed through ``admin_users_actions`` ends with a call
to ``record_audit`` so the Audit tab of the user drawer can replay
exactly who did what, and when.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.pagination import build_cursor_response, decode_cursor
from models.portal.audit import AdminAuditLog


async def record_audit(
    db: AsyncSession,
    *,
    admin_user_id: int | None,
    target_user_id: int | None,
    action: str,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    commit: bool = True,
) -> AdminAuditLog:
    """Append an entry to the audit log.

    Set ``commit=False`` to enrol this row inside an existing
    transaction (caller is then responsible for committing).
    """
    entry = AdminAuditLog(
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        action=action,
        payload=payload,
        ip=(ip or "")[:64] or None,
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(entry)
    if commit:
        await db.commit()
        await db.refresh(entry)
    return entry


async def list_audit_for_user(
    db: AsyncSession,
    target_user_id: int,
    *,
    limit: int = 100,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Latest-first audit trail for a single user (drawer Audit tab)."""
    total = int((await db.execute(
        select(func.count(AdminAuditLog.id)).where(
            AdminAuditLog.target_user_id == target_user_id
        )
    )).scalar() or 0)
    q = select(AdminAuditLog).where(AdminAuditLog.target_user_id == target_user_id)
    decoded = decode_cursor(cursor) if cursor else None
    if decoded and decoded.get("id") is not None:
        q = q.where(AdminAuditLog.id < decoded["id"])
    rows = (await db.execute(
        q.order_by(AdminAuditLog.id.desc()).limit(limit)
    )).scalars().all()
    items = [
        {
            "id": r.id,
            "admin_user_id": r.admin_user_id,
            "action": r.action,
            "payload": r.payload,
            "ip": r.ip,
            "user_agent": r.user_agent,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return build_cursor_response(items, total, limit, cursor_field="id")
