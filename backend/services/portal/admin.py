"""Admin user management for portal."""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.settings import Setting
from models.portal.profile import UserProfile
from models.portal.request import RequestQuota
from services.portal.profiles import serialize_profile

logger = logging.getLogger("mediakeeper.portal.admin")


# ---------------------------------------------------------------------------
# Portal-wide admin settings (stored in the generic `settings` key/value
# table so we don't need a dedicated schema). Flags are exposed via the
# /admin/settings endpoints and consumed by the request-status serialisers
# to decide how much metadata to leak to non-admin users.
# ---------------------------------------------------------------------------

# Registry of supported settings. Booleans and integers are stored as
# strings in the generic ``settings`` key/value table and parsed back
# on read. Add a new key here + a matching field in the frontend
# AdminSettings.vue form.
PORTAL_SETTING_FLAGS: dict[str, bool] = {
    # When True, request responses strip `requested_by` for non-admin users
    # so nobody can tell who filed which request. Date stays visible.
    "portal.anonymize_requests": False,
}

PORTAL_SETTING_INTS: dict[str, tuple[int, int, int]] = {
    # (default, min, max) — how many items appear in the hero banner on
    # the Portal home (featured + trending combined). 0 hides the hero
    # entirely.
    "portal.hero_trend_count": (10, 0, 20),
}


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _parse_int(raw: str | None, default: int, min_val: int, max_val: int) -> int:
    if raw is None:
        return default
    try:
        return max(min_val, min(max_val, int(raw)))
    except (ValueError, TypeError):
        return default


async def get_portal_settings(db: AsyncSession) -> dict:
    """Read all Portal admin settings (booleans + integers)."""
    all_keys = list(PORTAL_SETTING_FLAGS.keys()) + list(PORTAL_SETTING_INTS.keys())
    rows = (await db.execute(
        select(Setting).where(Setting.key.in_(all_keys))
    )).scalars().all()
    stored = {r.key: r.value for r in rows}
    result: dict = {}
    for k, default in PORTAL_SETTING_FLAGS.items():
        result[k] = _parse_bool(stored.get(k), default)
    for k, (default, lo, hi) in PORTAL_SETTING_INTS.items():
        result[k] = _parse_int(stored.get(k), default, lo, hi)
    return result


async def get_portal_flag(db: AsyncSession, key: str) -> bool:
    """Single-flag read shortcut. Returns the default if the key is unknown."""
    if key not in PORTAL_SETTING_FLAGS:
        return False
    row = (await db.execute(
        select(Setting).where(Setting.key == key)
    )).scalar_one_or_none()
    return _parse_bool(row.value if row else None, PORTAL_SETTING_FLAGS[key])


async def get_portal_int(db: AsyncSession, key: str) -> int:
    """Single-int read shortcut. Returns the default if unknown."""
    if key not in PORTAL_SETTING_INTS:
        return 0
    default, lo, hi = PORTAL_SETTING_INTS[key]
    row = (await db.execute(
        select(Setting).where(Setting.key == key)
    )).scalar_one_or_none()
    return _parse_int(row.value if row else None, default, lo, hi)


async def update_portal_settings(
    db: AsyncSession, updates: dict
) -> dict:
    """
    Upsert a subset of Portal admin settings (booleans + integers).
    Unknown keys are silently ignored so a stale frontend can't poison
    the settings table. Returns the full refreshed settings dict.
    """
    for key, val in updates.items():
        if key in PORTAL_SETTING_FLAGS:
            value_str = "true" if val else "false"
        elif key in PORTAL_SETTING_INTS:
            _, lo, hi = PORTAL_SETTING_INTS[key]
            value_str = str(max(lo, min(hi, int(val))))
        else:
            logger.warning(f"[PORTAL_SETTINGS] ignoring unknown key: {key}")
            continue
        row = (await db.execute(
            select(Setting).where(Setting.key == key)
        )).scalar_one_or_none()
        if row:
            row.value = value_str
        else:
            db.add(Setting(key=key, value=value_str))
    await db.commit()
    return await get_portal_settings(db)


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
    logger.info(f"[ADMIN] user_id={user_id} role changed to {role}")
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
    logger.info(f"[ADMIN] user_id={user_id} active={active}")
    return {"success": True}


async def update_user_quota(
    db: AsyncSession, user_id: int, data: dict
) -> dict:
    """Admin: update quota settings for a user."""
    result = await db.execute(
        select(RequestQuota).where(RequestQuota.user_id == user_id)
    )
    quota = result.scalar_one_or_none()
    if not quota:
        return {"error": "not_found"}

    for key in ("max_allowed", "unlimited", "auto_approve", "mode"):
        if key in data:
            setattr(quota, key, data[key])
    db.add(quota)
    await db.commit()
    return {"success": True}


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
