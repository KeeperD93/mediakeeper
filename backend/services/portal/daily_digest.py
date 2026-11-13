"""Daily digest orchestrator for the Portal viewer.

Once-per-day overlay payload aggregating the viewer's blocks (who is greeted,
account expiry, news, the new Portal version, library additions, "for you"
items, upcoming events, monthly ranking, level progress, request quota, open
tickets, closest achievement, play-day streak). Leaf aggregators live in
:mod:`daily_digest_sources`, :mod:`daily_digest_account` and
:mod:`daily_digest_for_you` so this file stays focused on caching, the
viewer's preferences (dismissal, compact view) and composition.

The payload is cached in-memory for ~1h per (user_id, date, lang) triple so a
user re-opening the overlay — or navigating pages that remount the
layout — doesn't trigger a full re-aggregation. Dismissal is stored in
``user_preferences.portal_daily_digest_dismissed_date`` as a
``YYYY-MM-DD`` string so the frontend can skip rendering until tomorrow.
The library-additions block lists items added since the viewer last
caught up (a per-user seen watermark in the same prefs blob, 30-day
floor, capped); the watermark advances 24h after a dismiss so just-seen
items linger a day of manual re-opens, then drop off. The new Portal version
stays a week from the first close under it, marked new until the viewer opens it.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from constants.changelog import PORTAL_SEEN_VERSION_KEY
from constants.daily_digest import RELEASE_SHOWN_DAYS
from models.user import User
from services.instance_time import get_instance_zone, to_local
from services.portal import daily_digest_account as account
from services.portal import daily_digest_for_you as for_you
from services.portal import daily_digest_sources as sources
from services.portal.profiles import get_or_create_profile
from services.settings import get_user_preferences, upsert_user_preferences

logger = logging.getLogger("mediakeeper.portal.daily_digest")

_PREF_KEY_DISMISSED_DATE = "portal_daily_digest_dismissed_date"
_PREF_KEY_DISMISSED_AT = "portal_daily_digest_dismissed_at"
_PREF_KEY_SEEN_AT = "portal_daily_digest_recent_seen_at"
_PREF_KEY_COMPACT = "portal_daily_digest_compact"
_PREF_KEY_RELEASE = "portal_daily_digest_release"
_CACHE_TTL_SEC = 3600
_GRACE_HOURS = 24
_MAX_LOOKBACK_DAYS = 30

# Cache: (user_id, date_iso, lang) -> (expires_at_epoch, payload). lang is part
# of the key because the payload re-resolves media titles/synopsis per viewer
# locale; a lang-agnostic key would serve the first-cached language to all.
_digest_cache: dict[tuple[int, str, str], tuple[float, dict]] = {}


async def _today_iso(db: AsyncSession) -> str:
    """Today on the calendar of the instance: the overlay comes back at its midnight."""
    zone = await get_instance_zone(db)
    return to_local(datetime.now(timezone.utc), zone).date().isoformat()


def _cache_get(user_id: int, date_iso: str, lang: str) -> dict | None:
    key = (user_id, date_iso, lang)
    hit = _digest_cache.get(key)
    if not hit:
        return None
    expires_at, payload = hit
    if expires_at < time.time():
        _digest_cache.pop(key, None)
        return None
    return payload


def _cache_set(user_id: int, date_iso: str, lang: str, payload: dict) -> None:
    _digest_cache[(user_id, date_iso, lang)] = (time.time() + _CACHE_TTL_SEC, payload)


def invalidate_cache(user_id: int) -> None:
    """Drop cached payload for a user (used on dismiss so reopens don't
    keep serving stale content)."""
    for key in list(_digest_cache.keys()):
        if key[0] == user_id:
            _digest_cache.pop(key, None)


async def _load_prefs(db: AsyncSession, user_id: int, *, lock_row: bool = False) -> dict:
    row = await get_user_preferences(db, user_id, lock_row=lock_row)
    if not row or not row.preferences:
        return {}
    try:
        return json.loads(row.preferences) or {}
    except (ValueError, TypeError):
        return {}


async def is_dismissed_today(db: AsyncSession, user_id: int) -> bool:
    prefs = await _load_prefs(db, user_id)
    return prefs.get(_PREF_KEY_DISMISSED_DATE) == await _today_iso(db)


async def is_compact(db: AsyncSession, user_id: int) -> bool:
    """The view the viewer picked for the overlay; the full one until they choose."""
    return (await _load_prefs(db, user_id)).get(_PREF_KEY_COMPACT) is True


async def set_compact(db: AsyncSession, user_id: int, compact: bool) -> bool:
    """Save the picked view, under a row lock so a concurrent locked write to the
    same preferences JSON (a dismissal) is not lost."""
    prefs = await _load_prefs(db, user_id, lock_row=True)
    prefs[_PREF_KEY_COMPACT] = compact
    await upsert_user_preferences(db, user_id, preferences=json.dumps(prefs))
    return compact


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


def _release_since(prefs: dict, version: str) -> datetime | None:
    """When the viewer first closed a digest under ``version``: its week starts there."""
    record = prefs.get(_PREF_KEY_RELEASE)
    if isinstance(record, dict) and record.get("version") == version:
        return _parse_dt(record.get("since"))
    return None


def _release_block(release: dict | None, prefs: dict, now: datetime) -> dict | None:
    """The new Portal version during its week, marked new until the viewer opens it."""
    if not release:
        return None
    since = _release_since(prefs, release["version"])
    if since and now - since >= timedelta(days=RELEASE_SHOWN_DAYS):
        return None
    return {**release, "is_new": prefs.get(PORTAL_SEEN_VERSION_KEY) != release["version"]}


async def mark_dismissed(
    db: AsyncSession, user_id: int, *, release_version: str | None = None,
) -> str:
    """Record today's date + the dismiss instant, then drop the cache.

    ``dismissed_date`` gates the once-per-day auto-show (unchanged).
    ``dismissed_at`` arms the 24h grace; before overwriting it, a *prior*
    dismiss whose grace has already elapsed is promoted into the seen
    watermark so the catch-up window doesn't reset back to the 30-day
    floor. This is the only place the watermark is persisted, keeping the
    GET read path side-effect free. Read under a row lock, like the compact
    view write, so neither loses the other. The first close under
    ``release_version`` starts the week the new version stays in the digest.
    """
    prefs = await _load_prefs(db, user_id, lock_row=True)
    now = datetime.now(timezone.utc)
    prev = _parse_dt(prefs.get(_PREF_KEY_DISMISSED_AT))
    if prev and now - prev >= timedelta(hours=_GRACE_HOURS):
        seen = _parse_dt(prefs.get(_PREF_KEY_SEEN_AT))
        prefs[_PREF_KEY_SEEN_AT] = (max(seen, prev) if seen else prev).isoformat()
    if release_version and _release_since(prefs, release_version) is None:
        prefs[_PREF_KEY_RELEASE] = {"version": release_version, "since": now.isoformat()}
    today = await _today_iso(db)
    prefs[_PREF_KEY_DISMISSED_DATE] = today
    prefs[_PREF_KEY_DISMISSED_AT] = now.isoformat()
    await upsert_user_preferences(db, user_id, preferences=json.dumps(prefs))
    invalidate_cache(user_id)
    return today


async def build_digest(
    db: AsyncSession,
    user: User,
    *,
    use_cache: bool = True,
    lang: str = "fr",
    name_lang: str = "fr",
    release: dict | None = None,
) -> dict[str, Any]:
    """Aggregate every digest block into a single payload.

    ``lang`` is the viewer's locale (media titles, cache key); ``name_lang`` is
    it reduced to the two languages the server writes names in. ``use_cache``
    lets the manual-open flow (avatar menu) bypass the 1h cache when the user
    explicitly asks for a fresh view. ``release`` is the current Portal version
    as its changelog describes it, read by the caller.
    """
    now = datetime.now(timezone.utc)
    zone = await get_instance_zone(db)
    date_iso = to_local(now, zone).date().isoformat()
    if use_cache:
        cached = _cache_get(user.id, date_iso, lang)
        if cached is not None:
            return cached

    profile = await get_or_create_profile(db, user)

    prefs = await _load_prefs(db, user.id)
    cutoff = _recent_cutoff(prefs, now)
    recent_adds = await sources.recent_adds(db, since=cutoff, lang=lang)
    events = await sources.upcoming_events(db, user.id)
    ranking = await sources.ranking_snapshot(db, user, lang=name_lang)
    quota = await sources.quota_snapshot(db, user.id)
    tickets_open = await sources.open_tickets_count(db, user.id)
    streak = await sources.current_streak(db, user, profile)
    next_ach = await sources.closest_achievement(db, user.id)
    news = await sources.latest_news(db, user.id)
    for_you_items = await for_you.recent(db, user.id, since=cutoff)
    expiry = account.expiry(profile, now=now, zone=zone)
    level = {
        **sources.level_info(profile),
        "xp_yesterday": await account.xp_yesterday(db, user.id, now=now, zone=zone),
    }
    release_block = _release_block(release, prefs, now)

    # Already read news or an already opened version alone are not worth opening the overlay for.
    has_content = bool(
        recent_adds or events or next_ach or streak
        or ranking["position"] or quota["used"] or tickets_open or level["xp"]
        or expiry or for_you_items or any(item["is_new"] for item in news)
        or (release_block and release_block["is_new"])
    )

    payload = {
        "date": date_iso,
        "empty": not has_content,
        "me": account.me(profile, name_lang),
        "expiry": expiry,
        "news": news,
        "release": release_block,
        "for_you": for_you_items,
        "level": level,
        "recent_adds": recent_adds,
        "events": events,
        "ranking": ranking,
        "quota": quota,
        "tickets_open": tickets_open,
        "streak": streak,
        "next_achievement": next_ach,
    }
    _cache_set(user.id, date_iso, lang, payload)
    return payload


__all__ = [
    "build_digest",
    "invalidate_cache",
    "is_compact",
    "is_dismissed_today",
    "mark_dismissed",
    "set_compact",
]
