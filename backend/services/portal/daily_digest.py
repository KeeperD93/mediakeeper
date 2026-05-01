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
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.settings import get_user_preferences, upsert_user_preferences
from services.portal.profile_serializers import _resolve_avatar_url
from services.portal.profiles import get_or_create_profile
from services.portal import daily_digest_sources as sources

logger = logging.getLogger("mediakeeper.portal.daily_digest")

_PREF_KEY_DISMISSED_DATE = "portal_daily_digest_dismissed_date"
_CACHE_TTL_SEC = 3600

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


async def mark_dismissed(db: AsyncSession, user_id: int) -> str:
    """Store today's date as the dismissed marker and drop the cache."""
    prefs = await _load_prefs(db, user_id)
    today = _today_iso()
    prefs[_PREF_KEY_DISMISSED_DATE] = today
    await upsert_user_preferences(db, user_id, preferences=json.dumps(prefs))
    invalidate_cache(user_id)
    return today


async def build_digest(
    db: AsyncSession, user: User, *, use_cache: bool = True,
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

    recent_adds = await sources.recent_adds(db)
    events = await sources.upcoming_events(db, user.id)
    ranking = await sources.ranking_snapshot(db, user)
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
