"""Admin user management for portal."""
import logging
import re
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import normalize_locale
from models.user import User
from models.settings import Setting
from models.portal.profile import UserProfile
from services.portal._html_sanitize import sanitize_html
from services.portal.profiles import serialize_profile
from services.portal.requests_quota import get_or_create_quota
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import ACTION_USER_QUOTA_CHANGED

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
    # When True, non-admin users may request pornographic content (TMDB
    # adult keywords) once they disable hide_adult. Default False: even a
    # viewer who unhides adult content cannot file such a request.
    "portal.allow_adult_requests": False,
    # When True, the heart panel surfaces the operator's own donation link
    # + message to every portal user. Independent of the static MediaKeeper
    # support links (admin-only). Has no effect until a link is also set.
    "portal.donation.enabled": False,
}

PORTAL_SETTING_INTS: dict[str, tuple[int, int, int]] = {
    # (default, min, max) — how many items appear in the hero banner on
    # the Portal home (featured + trending combined). 0 hides the hero
    # entirely.
    "portal.hero_trend_count": (10, 0, 20),
    # Auto-cleanup window for fulfilled (``available``) requests, in
    # days. 0 disables the hygiene job. The scheduler handler reads the
    # same key directly via ``requests_cleanup.get_cleanup_days``.
    "requests.auto_cleanup_days": (0, 0, 365),
    # Cinema-room capacity bounds for the event creator. The creator
    # picks ``MKEvent.max_participants`` from {5, 10, 15, 20} ∩ [min,
    # max]. Step is 5 (see ``PORTAL_EVENT_CAPACITY_STEP``). Defaults
    # keep the historical 50-seat pool out of reach and align with the
    # mobile-friendly layout (max 20 seats on a 4×5 grid).
    "portal.events.max_participants_min": (5, 5, 20),
    "portal.events.max_participants_max": (20, 5, 20),
}

# String settings. ``portal.default_language`` is the instance-wide default
# portal locale — a per-user ``user_profiles.language`` NULL inherits it, and
# blank here means inherit ``MK_DEFAULT_LOCALE``. Normalised to a 2-letter base
# on write.
PORTAL_SETTING_STRINGS: dict[str, str] = {
    "portal.default_language": "",
}

# Free-text string settings — stored verbatim (trimmed + length-capped),
# NOT locale-normalised like PORTAL_SETTING_STRINGS. Value is
# ``(default, max_len)``. The donation link/message power the heart
# "support" panel surfaced to every portal user once the operator turns
# on ``portal.donation.enabled``.
PORTAL_SETTING_FREETEXT: dict[str, tuple[str, int]] = {
    "portal.donation.url": ("", 500),
    # Optional custom label for the operator's donation button; blank falls
    # back to the translated default on the frontend.
    "portal.donation.button_label": ("", 60),
}

# Rich-text (WYSIWYG) settings — run through the shared bleach pipeline on
# write and rendered via ``v-html`` on read (same boundary as the GDPR
# privacy texts / Help Center). Value is the max raw length accepted before
# sanitising.
PORTAL_SETTING_HTML: dict[str, int] = {
    "portal.donation.message": 4000,
}

# Capacity values are always multiples of this step (radio chips
# 5/10/15/20 in the create-event picker). Exported for the admin
# patch endpoint to clamp client input and for the create-event
# schema validator on the way in.
PORTAL_EVENT_CAPACITY_STEP = 5


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


def _clean_freetext(key: str, raw) -> str:
    """Trim + length-cap a free-text setting. The donation URL additionally
    must be an http(s) link — anything else (javascript:, data:, ...) is
    dropped, since the value is rendered as a user-facing link."""
    _default, max_len = PORTAL_SETTING_FREETEXT[key]
    text = ("" if raw is None else str(raw)).strip()[:max_len]
    if key == "portal.donation.url" and text and not text.lower().startswith(
        ("http://", "https://")
    ):
        return ""
    return text


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_html(key: str, raw) -> str:
    """Sanitise a WYSIWYG value through the shared bleach pipeline, then
    normalise visually-empty content (e.g. ``<p></p>`` from an emptied
    editor) to "" so the frontend can fall back to its default text."""
    max_len = PORTAL_SETTING_HTML[key]
    cleaned = sanitize_html(("" if raw is None else str(raw))[:max_len])
    if not _HTML_TAG_RE.sub("", cleaned).strip() and "<img" not in cleaned.lower():
        return ""
    return cleaned


async def get_portal_settings(db: AsyncSession) -> dict:
    """Read all Portal admin settings (booleans + integers + strings)."""
    all_keys = (
        list(PORTAL_SETTING_FLAGS.keys())
        + list(PORTAL_SETTING_INTS.keys())
        + list(PORTAL_SETTING_STRINGS.keys())
        + list(PORTAL_SETTING_FREETEXT.keys())
        + list(PORTAL_SETTING_HTML.keys())
    )
    rows = (await db.execute(
        select(Setting).where(Setting.key.in_(all_keys))
    )).scalars().all()
    stored = {r.key: r.value for r in rows}
    result: dict = {}
    for k, default in PORTAL_SETTING_FLAGS.items():
        result[k] = _parse_bool(stored.get(k), default)
    for k, (default, lo, hi) in PORTAL_SETTING_INTS.items():
        result[k] = _parse_int(stored.get(k), default, lo, hi)
    for k, default in PORTAL_SETTING_STRINGS.items():
        result[k] = stored.get(k) or default
    for k, (default, _max_len) in PORTAL_SETTING_FREETEXT.items():
        result[k] = stored.get(k) or default
    for k in PORTAL_SETTING_HTML:
        result[k] = stored.get(k) or ""
    return result


async def get_donation_config(db: AsyncSession) -> dict:
    """Operator donation config for the heart panel, shared by the portal
    ``ui`` payload and the backoffice top-bar read. ``enabled`` is True only
    when the operator turned it on AND set a link, so callers can gate the
    heart on this single flag."""
    s = await get_portal_settings(db)
    url = s.get("portal.donation.url", "")
    enabled = bool(s.get("portal.donation.enabled")) and bool(url)
    return {
        "enabled": enabled,
        "url": url if enabled else "",
        "message": s.get("portal.donation.message", "") if enabled else "",
        "button_label": s.get("portal.donation.button_label", "") if enabled else "",
    }


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


_EVENT_CAPACITY_KEYS = {
    "portal.events.max_participants_min",
    "portal.events.max_participants_max",
}


def _snap_to_step(value: int, step: int, lo: int, hi: int) -> int:
    """Clamp ``value`` to [lo, hi] then snap to the nearest ``step``
    multiple within that range so admin inputs from a stale frontend
    cannot land between two radio-chip values."""
    clamped = max(lo, min(hi, value))
    snapped = round(clamped / step) * step
    return max(lo, min(hi, snapped))


async def update_portal_settings(
    db: AsyncSession, updates: dict
) -> dict:
    """
    Upsert a subset of Portal admin settings (booleans + integers + strings).
    Unknown keys are silently ignored so a stale frontend can't poison
    the settings table. Returns the full refreshed settings dict.
    """
    # Capacity bounds have to land on a step-5 multiple AND keep
    # min ≤ max, even when the admin pushes a single slider. Resolve
    # them together with the current stored values so a partial PATCH
    # cannot leave the table in a min > max state.
    pending_capacity: dict[str, int] = {}
    for key in _EVENT_CAPACITY_KEYS:
        if key in updates:
            _, lo, hi = PORTAL_SETTING_INTS[key]
            pending_capacity[key] = _snap_to_step(
                int(updates[key]),
                PORTAL_EVENT_CAPACITY_STEP,
                lo,
                hi,
            )
    if pending_capacity:
        current = await get_portal_settings(db)
        proposed_min = pending_capacity.get(
            "portal.events.max_participants_min",
            current["portal.events.max_participants_min"],
        )
        proposed_max = pending_capacity.get(
            "portal.events.max_participants_max",
            current["portal.events.max_participants_max"],
        )
        if proposed_max < proposed_min:
            proposed_max = proposed_min
        pending_capacity["portal.events.max_participants_min"] = proposed_min
        pending_capacity["portal.events.max_participants_max"] = proposed_max

    for key, val in updates.items():
        if key in PORTAL_SETTING_FLAGS:
            value_str = "true" if val else "false"
        elif key in pending_capacity:
            value_str = str(pending_capacity[key])
        elif key in PORTAL_SETTING_INTS:
            _, lo, hi = PORTAL_SETTING_INTS[key]
            value_str = str(max(lo, min(hi, int(val))))
        elif key in PORTAL_SETTING_STRINGS:
            # Normalise to a 2-letter base ("fr-FR" -> "fr"); invalid/blank = inherit.
            value_str = normalize_locale(val) or ""
        elif key in PORTAL_SETTING_FREETEXT:
            value_str = _clean_freetext(key, val)
        elif key in PORTAL_SETTING_HTML:
            value_str = _clean_html(key, val)
        else:
            logger.warning("[PORTAL_SETTINGS] ignoring unknown key: %s", key)
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


async def get_event_capacity_bounds(db: AsyncSession) -> tuple[int, int]:
    """Return ``(min, max)`` capacity for new events. Used by the
    create-event endpoint to validate the user-picked value."""
    settings = await get_portal_settings(db)
    return (
        settings["portal.events.max_participants_min"],
        settings["portal.events.max_participants_max"],
    )


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
    # drifts it from there.
    if data.get("mode") == "auto" and quota.mode != "auto":
        from services.portal.quota_auto import START_CAP
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
