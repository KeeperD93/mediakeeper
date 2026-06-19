"""Leaf aggregators feeding the Portal daily digest.

Each helper is a standalone, defensively-wrapped call into an existing
service (Emby, events, ranking, quota, tickets, achievements, playback).
They live in this sibling module so the orchestrator in
``daily_digest.py`` stays under the 300-line cap with just the caching,
dismissal and composition logic.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.portal.profile import UserProfile
from models.portal.ticket import Ticket
from services.portal.available import get_recently_added
from services.portal.mk_events_crud import list_for_user as list_events_for_user
from services.portal.profile_stats_ranking import (
    compute_ranking, title_for_level, tier_for_level,
)
from services.portal.requests_quota import get_user_quota
from services.portal.exclusions import get_exclusion_filters
from services.portal.personal_utils import _playback_user_filter
from services.portal.profile_stats_playback import compute_streak
from services.portal.achievements_profile import get_achievements_for_profile
from services.portal.xp import MAX_LEVEL, xp_for_level

logger = logging.getLogger("mediakeeper.portal.daily_digest")

RECENT_ADDS_FETCH_LIMIT = 80
RECENT_ADDS_CAP = 30
EVENTS_WINDOW_DAYS = 7


def _parse_emby_iso(raw: str) -> datetime | None:
    """Parse Emby's full ``DateCreated`` (UTC ISO, e.g. ``...Z`` with up to 7
    fractional digits) into a tz-aware UTC datetime, or ``None`` when absent or
    unparseable. ``fromisoformat`` accepts at most 6 fractional digits, so the
    Emby surplus is trimmed first."""
    if not raw:
        return None
    s = re.sub(r"(\.\d{6})\d+", r"\1", raw.replace("Z", "+00:00"))
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def recent_adds(
    db: AsyncSession, *, since: datetime, cap: int = RECENT_ADDS_CAP
) -> list[dict]:
    """Emby items added since the viewer last caught up, newest first.

    ``since`` is the viewer's seen watermark (see
    :func:`daily_digest._recent_cutoff`); items strictly newer than it are
    kept, capped at ``cap`` posters. The comparison uses the full
    ``date_created_at`` timestamp, so an item added later on the *same*
    calendar day as the watermark is still surfaced. Only when Emby exposed no
    sub-day timestamp do we fall back to the day-granular ``date_created``.
    """
    since_date = since.astimezone(timezone.utc).date().isoformat()

    def _is_new(it: dict) -> bool:
        created_at = _parse_emby_iso(it.get("date_created_at") or "")
        if created_at is not None:
            return created_at > since
        return (it.get("date_created") or "") > since_date

    try:
        items = await get_recently_added(db, limit=RECENT_ADDS_FETCH_LIMIT)
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] recent adds failed: %s", e)
        return []
    kept = [it for it in items if _is_new(it)]
    return [
        {
            "tmdb_id": it.get("tmdb_id"),
            "emby_item_id": it.get("emby_item_id"),
            "title": it.get("title"),
            "year": it.get("year"),
            "media_type": it.get("media_type"),
            "poster_url": it.get("poster_url"),
            "date_created": it.get("date_created"),
        }
        for it in kept[:cap]
    ]


async def upcoming_events(db: AsyncSession, user_id: int) -> list[dict]:
    """Future events the user is involved in, capped at the next 7 days."""
    try:
        rows = await list_events_for_user(db, user_id)
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] events failed: %s", e)
        return []
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=EVENTS_WINDOW_DAYS)
    out: list[dict] = []
    for ev in rows:
        sched_raw = ev.get("scheduled_at")
        if not sched_raw:
            continue
        try:
            sched_dt = datetime.fromisoformat(sched_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if sched_dt.tzinfo is None:
            sched_dt = sched_dt.replace(tzinfo=timezone.utc)
        if not (now <= sched_dt <= horizon):
            continue
        out.append({
            "id": ev.get("id"),
            "title": ev.get("title"),
            "kind": ev.get("kind"),
            "scheduled_at": sched_raw,
        })
    return out


async def open_tickets_count(db: AsyncSession, user_id: int) -> int:
    try:
        result = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == user_id,
                Ticket.status == "open",
            )
        )
        return int(result.scalar() or 0)
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] tickets count failed: %s", e)
        return 0


async def closest_achievement(db: AsyncSession, user_id: int) -> dict | None:
    try:
        payload = await get_achievements_for_profile(db, user_id)
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] achievements failed: %s", e)
        return None
    nxt = payload.get("next_achievement")
    if not nxt:
        return None
    return {
        "id": nxt.get("id"),
        "name_key": nxt.get("name_key"),
        "description_key": nxt.get("description_key"),
        "icon": nxt.get("icon"),
        "tier": nxt.get("tier"),
        "progress": nxt.get("progress"),
        "threshold": nxt.get("threshold"),
        "remaining": max(0, (nxt.get("threshold") or 0) - (nxt.get("progress") or 0)),
    }


async def current_streak(db: AsyncSession, user: User, profile: UserProfile) -> int:
    try:
        excl_filters = await get_exclusion_filters(db)
        user_filter = _playback_user_filter(user, profile)
        return int(await compute_streak(db, user_filter, excl_filters) or 0)
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] streak failed: %s", e)
        return 0


async def ranking_snapshot(
    db: AsyncSession, user: User, *, lang: str = "fr"
) -> dict:
    """Rank + slimmed top-3 slice for the digest's mini-leaderboard widget."""
    try:
        r = await compute_ranking(db, user, lang=lang)
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] ranking failed: %s", e)
        return {"position": 0, "total": 0, "movement": 0, "top3": []}
    # Same shape as the dashboard ``LeaderboardCard`` widget so the
    # daily-digest top 3 can render through the exact same component
    # (visual parity with the "Classement de ce mois" widget).
    def _project(entry: dict) -> dict:
        return {
            "rank": entry.get("rank"),
            "user_id": entry.get("user_id"),
            "display_name": entry.get("display_name"),
            "avatar_url": entry.get("avatar_url"),
            "tier": entry.get("tier"),
            "title_key": entry.get("title_key"),
            "selected_title": entry.get("selected_title"),
            "title_tier": entry.get("title_tier"),
            "movement": entry.get("movement") or 0,
            "month_xp": entry.get("month_xp") or 0,
            "is_current_user": entry.get("is_current_user") or False,
        }

    full_board = r.get("leaderboard") or []
    top3 = [_project(e) for e in full_board[:3]]

    # Append the current user as a 4th row when they're outside the
    # podium so the digest mirrors the leaderboard widget's "you sit
    # here" affordance rather than hiding their position entirely.
    if not any(row["is_current_user"] for row in top3):
        me = next((e for e in full_board if e.get("is_current_user")), None)
        if me:
            top3.append(_project(me))
    return {
        "position": r.get("position") or 0,
        "total": r.get("total") or 0,
        "movement": r.get("movement") or 0,
        "top3": top3,
    }


def level_info(profile: UserProfile) -> dict:
    """Current-level XP progress so the frontend can draw a progress bar."""
    level = int(getattr(profile, "level", 1) or 1)
    xp = int(getattr(profile, "xp", 0) or 0)
    maxed = level >= MAX_LEVEL
    xp_curr = xp_for_level(level)
    # At the cap there is no next level: the bar reads full and the next
    # threshold collapses onto the current one (mirrors useProfileXp).
    xp_next = xp_curr if maxed else xp_for_level(level + 1)
    span = max(1, xp_next - xp_curr)
    into = max(0, xp - xp_curr)
    return {
        "level": level,
        "xp": xp,
        "xp_current_level": xp_curr,
        "xp_next_level": xp_next,
        "xp_into_level": into,
        "percent": 100 if maxed else min(100, round(100 * into / span)),
        "maxed": maxed,
        "title_key": title_for_level(level),
        "tier": tier_for_level(level),
    }


async def quota_snapshot(db: AsyncSession, user_id: int) -> dict:
    try:
        q = await get_user_quota(db, user_id)
    except Exception as e:  # noqa: BLE001
        logger.debug("[DIGEST] quota failed: %s", e)
        return {"used": 0, "max_allowed": 0, "unlimited": False, "remaining": 0}
    max_allowed = int(q.get("max_allowed") or 0)
    used = int(q.get("used") or 0)
    unlimited = bool(q.get("unlimited"))
    remaining = -1 if unlimited else max(0, max_allowed - used)
    return {
        "used": used,
        "max_allowed": max_allowed,
        "unlimited": unlimited,
        "remaining": remaining,
    }
