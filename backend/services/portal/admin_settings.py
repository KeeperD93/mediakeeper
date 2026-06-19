"""Portal-wide admin settings registry (generic key/value store).

Booleans, integers and strings are persisted as strings in the shared
``settings`` key/value table — no dedicated schema — and parsed back on read.
The values are exposed via the ``/admin/settings`` endpoints and consumed by
the request-status serialisers (how much metadata to leak to non-admin
users), the cinema-room capacity validator and the heart donation panel.

Add a new key here + a matching field in the frontend ``AdminSettings.vue``
form.
"""
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.quota import QUOTA_AUTO_DEFAULTS, QUOTA_BAND_MAX, QUOTA_BAND_MIN
from core.i18n import normalize_locale
from models.settings import Setting
from services.portal._html_sanitize import sanitize_html

logger = logging.getLogger("mediakeeper.portal.admin")


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
    # Master switch for the nightly engagement-based auto quota recompute.
    # ON by default; still a no-op unless users are in auto mode.
    "quota.auto.enabled": True,
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
    # Instance defaults for the automatic request-quota mode. ``min``/``max``
    # seed the per-user band (auto_min/auto_max) when an admin switches a user
    # to auto; the rest drive the nightly recompute. Defaults and the [min,
    # max] cap band come from constants/quota.py (single source).
    "quota.auto.min": (QUOTA_AUTO_DEFAULTS["min"], QUOTA_BAND_MIN, QUOTA_BAND_MAX),
    "quota.auto.max": (QUOTA_AUTO_DEFAULTS["max"], QUOTA_BAND_MIN, QUOTA_BAND_MAX),
    "quota.auto.window_days": (QUOTA_AUTO_DEFAULTS["window_days"], 1, 90),
    "quota.auto.grace_days": (QUOTA_AUTO_DEFAULTS["grace_days"], 0, 90),
    "quota.auto.up_step": (QUOTA_AUTO_DEFAULTS["up_step"], 1, 50),
    "quota.auto.down_step": (QUOTA_AUTO_DEFAULTS["down_step"], 1, 50),
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

_QUOTA_BAND_KEYS = {"quota.auto.min", "quota.auto.max"}


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

    # Auto-quota band keeps the same min ≤ max invariant as the event
    # capacity pair: resolve against stored values so a single-field PATCH
    # can't leave min > max. min > max is equalised (max := min), mirroring
    # the capacity reorder above.
    pending_quota: dict[str, int] = {}
    for key in _QUOTA_BAND_KEYS:
        if key in updates:
            _, lo, hi = PORTAL_SETTING_INTS[key]
            pending_quota[key] = max(lo, min(hi, int(updates[key])))
    if pending_quota:
        current = await get_portal_settings(db)
        q_min = pending_quota.get("quota.auto.min", current["quota.auto.min"])
        q_max = pending_quota.get("quota.auto.max", current["quota.auto.max"])
        if q_max < q_min:
            q_max = q_min
        pending_quota["quota.auto.min"] = q_min
        pending_quota["quota.auto.max"] = q_max

    for key, val in updates.items():
        if key in PORTAL_SETTING_FLAGS:
            value_str = "true" if val else "false"
        elif key in pending_capacity:
            value_str = str(pending_capacity[key])
        elif key in pending_quota:
            value_str = str(pending_quota[key])
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
