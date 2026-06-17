"""Admin user management for portal."""
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from services.portal.profiles import serialize_profile
from services.portal.requests_quota import get_or_create_quota
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import ACTION_USER_QUOTA_CHANGED

# Portal-wide settings moved to ``admin_settings``; re-exported so existing
# ``services.portal.admin`` import sites keep resolving.
from services.portal.admin_settings import (
    PORTAL_EVENT_CAPACITY_STEP,  # noqa: F401
    PORTAL_SETTING_FLAGS,  # noqa: F401
    get_donation_config,  # noqa: F401
    get_event_capacity_bounds,  # noqa: F401
    get_portal_flag,  # noqa: F401
    get_portal_int,
    get_portal_settings,  # noqa: F401
    update_portal_settings,  # noqa: F401
)

logger = logging.getLogger("mediakeeper.portal.admin")


async def list_portal_users(
    db: AsyncSession,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List all portal users with profiles."""
    query = select(UserProfile).order_by(UserProfile.id)
    count_q = select(func.count(UserProfile.id))

    if search:
        like = f"%{search}%"
        query = query.where(UserProfile.display_name.ilike(like))
        count_q = count_q.where(UserProfile.display_name.ilike(like))

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(query.offset(offset).limit(limit))
    items = [serialize_profile(p) for p in result.scalars().all()]
    return {"items": items, "total": total}


async def update_user_role(
    db: AsyncSession, user_id: int, role: str
) -> dict:
    """Change a user's role (admin/viewer)."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {"error": "not_found"}
    profile.role = role
    db.add(profile)
    await db.commit()
    logger.info("[ADMIN] user_id=%s role changed to %s", user_id, role)
    return {"success": True}


async def toggle_user_active(
    db: AsyncSession, user_id: int, active: bool
) -> dict:
    """Enable/disable a portal user account."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {"error": "not_found"}
    profile.account_active = active
    db.add(profile)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.is_active = active
        db.add(user)

    await db.commit()
    logger.info("[ADMIN] user_id=%s active=%s", user_id, active)
    return {"success": True}


async def update_user_quota(
    db: AsyncSession,
    user_id: int,
    data: dict,
    *,
    admin_user_id: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Admin: update a user's quota, recording a from/to audit entry for
    every field that actually changes. Creates the row on first edit
    (seeding the admin/moderator unlimited default via get_or_create_quota)."""
    quota = await get_or_create_quota(db, user_id)

    # Reject an inverted auto-mode range against the MERGED values — a
    # single-field PATCH may set only one bound.
    if data.get("auto_min", quota.auto_min) > data.get("auto_max", quota.auto_max):
        return {"error": "invalid_bounds"}

    # Switching to auto resets the working cap to the start value (clamped to
    # the band) so a high manual cap doesn't carry over; the nightly job then
    # drifts it from there. A plain flip (no band given) seeds the per-user
    # band from the instance defaults; an explicit band in this PATCH wins.
    if data.get("mode") == "auto" and quota.mode != "auto":
        from services.portal.quota_auto import START_CAP
        if "auto_min" not in data and "auto_max" not in data:
            inst_min = await get_portal_int(db, "quota.auto.min")
            inst_max = await get_portal_int(db, "quota.auto.max")
            data = {**data, "auto_min": min(inst_min, inst_max),
                    "auto_max": max(inst_min, inst_max)}
        lo = data.get("auto_min", quota.auto_min)
        hi = data.get("auto_max", quota.auto_max)
        data = {**data, "max_allowed": max(lo, min(hi, START_CAP))}

    changed: dict[str, dict] = {}
    for key in ("max_allowed", "unlimited", "auto_approve", "mode", "auto_min", "auto_max"):
        if key in data and getattr(quota, key) != data[key]:
            changed[key] = {"from": getattr(quota, key), "to": data[key]}
            setattr(quota, key, data[key])
    if not changed:
        return {"success": True, "changed": {}}
    db.add(quota)
    await record_audit(
        db,
        admin_user_id=admin_user_id,
        target_user_id=user_id,
        action=ACTION_USER_QUOTA_CHANGED,
        payload={"changed": changed, "source": "admin"},
        ip=ip,
        user_agent=user_agent,
        commit=False,
    )
    await db.commit()
    return {"success": True, "changed": changed}


async def toggle_chat(
    db: AsyncSession, user_id: int, enabled: bool
) -> dict:
    """Enable/disable chat for a user."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {"error": "not_found"}
    profile.chat_enabled = enabled
    db.add(profile)
    await db.commit()
    return {"success": True}


async def force_public_profile(
    db: AsyncSession, user_id: int, forced: bool | None
) -> dict:
    """Force a user's profile to be public (or remove override)."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {"error": "not_found"}
    profile.forced_public = forced
    if forced:
        profile.is_public = True
    db.add(profile)
    await db.commit()
    return {"success": True}


async def get_admin_stats(db: AsyncSession) -> dict:
    """Dashboard stats for admin — extended with weekly counters for the
    refurbished Admin Requests page top bar."""
    from datetime import datetime, timezone, timedelta
    from models.portal.request import MediaRequest
    from models.portal.ticket import Ticket

    total_users = (await db.execute(
        select(func.count(UserProfile.id))
    )).scalar() or 0

    pending_requests = (await db.execute(
        select(func.count(MediaRequest.id))
        .where(MediaRequest.status == "pending")
    )).scalar() or 0

    open_tickets = (await db.execute(
        select(func.count(Ticket.id))
        .where(Ticket.status == "open")
    )).scalar() or 0

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    approved_this_week = (await db.execute(
        select(func.count(MediaRequest.id))
        .where(
            MediaRequest.status.in_(("approved", "available")),
            MediaRequest.updated_at >= week_ago,
        )
    )).scalar() or 0

    rejected_this_week = (await db.execute(
        select(func.count(MediaRequest.id))
        .where(
            MediaRequest.status == "rejected",
            MediaRequest.updated_at >= week_ago,
        )
    )).scalar() or 0

    available_count = (await db.execute(
        select(func.count(MediaRequest.id))
        .where(MediaRequest.status == "available")
    )).scalar() or 0

    # All-time totals — surfaced as the "since the beginning" sub-line
    # under each top-bar stat so admins see the cumulative volume next
    # to the live/weekly counter.
    total_requests = (await db.execute(
        select(func.count(MediaRequest.id))
    )).scalar() or 0

    approved_total = (await db.execute(
        select(func.count(MediaRequest.id))
        .where(MediaRequest.status.in_(("approved", "available")))
    )).scalar() or 0

    rejected_total = (await db.execute(
        select(func.count(MediaRequest.id))
        .where(MediaRequest.status == "rejected")
    )).scalar() or 0

    return {
        "total_users": total_users,
        "pending_requests": pending_requests,
        "open_tickets": open_tickets,
        "approved_this_week": approved_this_week,
        "rejected_this_week": rejected_this_week,
        "available_count": available_count,
        "total_requests": total_requests,
        "approved_total": approved_total,
        "rejected_total": rejected_total,
    }
