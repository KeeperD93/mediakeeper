"""Daily digest orchestrator for the Portal viewer.

Once-per-day overlay payload aggregating eight blocks (library additions,
upcoming events, monthly ranking, level progress, request quota, open
tickets, closest achievement, play-day streak). Leaf aggregators live
in :mod:`daily_digest_sources` so this file stays focused on caching,
dismissal and composition.

The payload is cached in-memory for ~1h per (user_id, date) pair so a
user re-opening the overlay — or navigating pages that remount the
layout — doesn't trigger a full re-aggregation. Dismissal is stored in
``user_preferences.portal_daily_digest_dismissed_date`` as a
``YYYY-MM-DD`` string so the frontend can skip rendering until tomorrow.
The library-additions block lists items added since the viewer last
caught up (a per-user seen watermark in the same prefs blob, 30-day
floor, capped); the watermark advances 24h after a dismiss so just-seen
items linger a day of manual re-opens, then drop off.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.settings import get_user_preferences, upsert_user_preferences
from services.portal.profile_serializers import _resolve_avatar_url
from services.portal.profiles import get_or_create_profile
from services.portal import daily_digest_sources as sources

logger = logging.getLogger("mediakeeper.portal.daily_digest")

_PREF_KEY_DISMISSED_DATE = "portal_daily_digest_dismissed_date"
_PREF_KEY_DISMISSED_AT = "portal_daily_digest_dismissed_at"
_PREF_KEY_SEEN_AT = "portal_daily_digest_recent_seen_at"
_CACHE_TTL_SEC = 3600
_GRACE_HOURS = 24
_MAX_LOOKBACK_DAYS = 30

# Cache: (user_id, date_iso) -> (expires_at_epoch, payload)
_digest_cache: dict[tuple[int, str], tuple[float, dict]] = {}


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _cache_get(user_id: int, date_iso: str) -> dict | None:
    hit = _digest_cache.get((user_id, date_iso))
    if not hit:
        return None
    expires_at, payload = hit
    if expires_at < time.time():
        _digest_cache.pop((user_id, date_iso), None)
        return None
    return payload


def _cache_set(user_id: int, date_iso: str, payload: dict) -> None:
    _digest_cache[(user_id, date_iso)] = (time.time() + _CACHE_TTL_SEC, payload)


def invalidate_cache(user_id: int) -> None:
    """Drop cached payload for a user (used on dismiss so reopens don't
    keep serving stale content)."""
    for key in list(_digest_cache.keys()):
        if key[0] == user_id:
            _digest_cache.pop(key, None)


async def _load_prefs(db: AsyncSession, user_id: int) -> dict:
    row = await get_user_preferences(db, user_id)
    if not row or not row.preferences:
        return {}
    try:
        return json.loads(row.preferences) or {}
    except (ValueError, TypeError):
        return {}


async def is_dismissed_today(db: AsyncSession, user_id: int) -> bool:
    prefs = await _load_prefs(db, user_id)
    return prefs.get(_PREF_KEY_DISMISSED_DATE) == _today_iso()


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _recent_cutoff(prefs: dict, now: datetime) -> datetime:
    """Date floor for "added since the viewer last caught up" — pure read.

    Once the 24h grace after a dismiss has elapsed, that dismiss instant
    counts as the seen watermark (items shown in a session linger a day of
    manual re-opens, then drop off). A 30-day floor bounds a first-ever or
    long-absent viewer so the catch-up never dumps the whole library. A
    watermark in the future (clock skew / corrupted pref) is ignored rather
    than blacking out the list. The advance is *persisted* lazily by
    :func:`mark_dismissed`, never on this read path, so a GET never races a
    concurrent preferences write.
    """
    seen_at = _parse_dt(prefs.get(_PREF_KEY_SEEN_AT))
    if seen_at and seen_at > now:
        seen_at = None
    dismissed_at = _parse_dt(prefs.get(_PREF_KEY_DISMISSED_AT))
    if dismissed_at and now - dismissed_at >= timedelta(hours=_GRACE_HOURS):
        seen_at = max(seen_at, dismissed_at) if seen_at else dismissed_at
    floor = now - timedelta(days=_MAX_LOOKBACK_DAYS)
    return max(seen_at, floor) if seen_at else floor


async def mark_dismissed(db: AsyncSession, user_id: int) -> str:
    """Record today's date + the dismiss instant, then drop the cache.

    ``dismissed_date`` gates the once-per-day auto-show (unchanged).
    ``dismissed_at`` arms the 24h grace; before overwriting it, a *prior*
    dismiss whose grace has already elapsed is promoted into the seen
    watermark so the catch-up window doesn't reset back to the 30-day
    floor. This is the only place the watermark is persisted, keeping the
    GET read path side-effect free.
    """
    prefs = await _load_prefs(db, user_id)
    now = datetime.now(timezone.utc)
    prev = _parse_dt(prefs.get(_PREF_KEY_DISMISSED_AT))
    if prev and now - prev >= timedelta(hours=_GRACE_HOURS):
        seen = _parse_dt(prefs.get(_PREF_KEY_SEEN_AT))
        prefs[_PREF_KEY_SEEN_AT] = (max(seen, prev) if seen else prev).isoformat()
    today = now.date().isoformat()
    prefs[_PREF_KEY_DISMISSED_DATE] = today
    prefs[_PREF_KEY_DISMISSED_AT] = now.isoformat()
    await upsert_user_preferences(db, user_id, preferences=json.dumps(prefs))
    invalidate_cache(user_id)
    return today


async def build_digest(
    db: AsyncSession, user: User, *, use_cache: bool = True, lang: str = "fr",
) -> dict[str, Any]:
    """Aggregate every digest block into a single payload.

    ``use_cache`` lets the manual-open flow (avatar menu) bypass the
    1h cache when the user explicitly asks for a fresh view.
    """
    date_iso = _today_iso()
    if use_cache:
        cached = _cache_get(user.id, date_iso)
        if cached is not None:
            return cached

    profile = await get_or_create_profile(db, user)

    prefs = await _load_prefs(db, user.id)
    cutoff = _recent_cutoff(prefs, datetime.now(timezone.utc))
    recent_adds = await sources.recent_adds(db, since=cutoff)
    events = await sources.upcoming_events(db, user.id)
    ranking = await sources.ranking_snapshot(db, user, lang=lang)
    quota = await sources.quota_snapshot(db, user.id)
    tickets_open = await sources.open_tickets_count(db, user.id)
    streak = await sources.current_streak(db, user, profile)
    next_ach = await sources.closest_achievement(db, user.id)
    level = sources.level_info(profile)

    has_content = bool(
        recent_adds or events or next_ach or streak
        or ranking["position"] or quota["used"] or tickets_open or level["xp"]
    )

    payload = {
        "date": date_iso,
        "empty": not has_content,
        "display_name": profile.display_name or user.username,
        "avatar_url": _resolve_avatar_url(profile),
        "level": level,
        "recent_adds": recent_adds,
        "events": events,
        "ranking": ranking,
        "quota": quota,
        "tickets_open": tickets_open,
        "streak": streak,
        "next_achievement": next_ach,
    }
    _cache_set(user.id, date_iso, payload)
    return payload


__all__ = ["build_digest", "is_dismissed_today", "mark_dismissed", "invalidate_cache"]
