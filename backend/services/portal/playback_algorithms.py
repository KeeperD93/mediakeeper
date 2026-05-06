"""Pure-Python algorithms over ``playback_sessions`` for the
``secret_allnight``, ``secret_no_life`` and ``secret_king`` trophies.

These three checks share the same data dependency as the cross-user
overlap helpers in :mod:`playback_overlap`: a single read of the
viewer's own ``PlaybackSession`` rows (``secret_king`` additionally
needs the cross-user view to compute monthly leaderboards). All date
arithmetic is performed in Python so the helpers behave identically on
SQLite (tests) and PostgreSQL (prod), and ``OPEN_SESSION_FALLBACK`` is
reused so an unclosed session is treated the same way the rest of the
pipeline already does (4h cap from the collector).

Conventions:

* All timestamps are normalised to UTC via :func:`_as_utc` before any
  comparison; naive datetimes are assumed UTC.
* ``PlaybackSession.user_id`` stores the **Emby user_id string**, not
  the MK ``users.id``. Callers resolve the matching Emby IDs upstream
  (the secrets-b module already does this for ``secret_lonely`` /
  ``secret_sync``) and pass them down via ``emby_user_ids``.
* ``secret_king`` enforces an **N >= 2 distinct active users per month**
  guard: a month with a single active user is *skipped* (it does not
  break the consecutive chain, but it does not count toward it either).
  This mirrors the anti-trivial guard applied to ``secret_lonely`` /
  ``secret_sync`` — a single-user instance must not unlock a leaderboard
  trophy by default.
* ``secret_allnight`` allows up to 5-minute gaps between consecutive
  sessions (and a 40-minute cumulative budget across the 8-hour
  window) to absorb very short pauses (toilet breaks, device handoff)
  without invalidating an otherwise-continuous all-nighter.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from services.portal.playback_overlap import (
    OPEN_SESSION_FALLBACK,
    _as_utc,
    _effective_end,
)


__all__ = [
    "OPEN_SESSION_FALLBACK",
    "has_all_night_chain",
    "has_24h_in_48h_window",
    "has_12_consecutive_top1_months",
]


# Tunables for ``secret_allnight``. Kept module-level so the values are
# discoverable from tests and the docstrings above stay authoritative.
ALL_NIGHT_MAX_GAP = timedelta(minutes=5)
ALL_NIGHT_TOTAL_GAP_BUDGET = timedelta(minutes=40)
ALL_NIGHT_WINDOW_START_HOUR = 22  # inclusive (UTC)
ALL_NIGHT_WINDOW_END_HOUR = 6     # inclusive (UTC, on day J+1)

NO_LIFE_WINDOW = timedelta(hours=48)
NO_LIFE_TARGET_SECONDS = 24 * 3600

KING_REQUIRED_CONSECUTIVE_MONTHS = 12
KING_MIN_DISTINCT_USERS_PER_MONTH = 2


async def _load_user_sessions(
    db: AsyncSession, emby_user_ids: list[str]
) -> list[tuple[datetime, datetime]]:
    """Return ``[(start_utc, end_utc), ...]`` sorted by start, NULL ends bounded."""
    if not emby_user_ids:
        return []
    rows = (await db.execute(
        select(PlaybackSession.started_at, PlaybackSession.ended_at)
        .where(PlaybackSession.user_id.in_(emby_user_ids))
    )).all()

    sessions: list[tuple[datetime, datetime]] = []
    for started_at, ended_at in rows:
        start = _as_utc(started_at)
        if start is None:
            continue
        end = _effective_end(start, _as_utc(ended_at))
        sessions.append((start, end))
    sessions.sort(key=lambda pair: pair[0])
    return sessions


# ── secret_allnight ────────────────────────────────────────────────────


async def has_all_night_chain(
    db: AsyncSession, emby_user_ids: list[str]
) -> bool:
    """``True`` iff a continuous chain of sessions covers 22:00 → 06:00 UTC.

    Definition of "chain": consecutive sessions are part of the same chain
    when ``next.start - prev.end <= ALL_NIGHT_MAX_GAP`` AND the cumulative
    gap budget of the chain stays under ``ALL_NIGHT_TOTAL_GAP_BUDGET``.
    The window spans ``[22:00 UTC day J, 06:00 UTC day J+1]`` and a chain
    is considered to "cover" it iff
    ``chain_start <= 22:00 UTC`` and ``chain_end >= 06:00 UTC`` for some
    anchor day ``J`` derived from the chain's own time range.
    """
    sessions = await _load_user_sessions(db, emby_user_ids)
    if not sessions:
        return False

    chains: list[tuple[datetime, datetime]] = []
    chain_start, chain_end = sessions[0]
    cumulative_gap = timedelta(0)

    for next_start, next_end in sessions[1:]:
        gap = next_start - chain_end
        if gap < timedelta(0):
            # Overlapping rows (e.g. multi-device): no gap, just extend.
            chain_end = max(chain_end, next_end)
            continue
        if (
            gap <= ALL_NIGHT_MAX_GAP
            and cumulative_gap + gap <= ALL_NIGHT_TOTAL_GAP_BUDGET
        ):
            cumulative_gap += gap
            chain_end = max(chain_end, next_end)
            continue
        chains.append((chain_start, chain_end))
        chain_start, chain_end = next_start, next_end
        cumulative_gap = timedelta(0)
    chains.append((chain_start, chain_end))

    for cs, ce in chains:
        if _chain_covers_all_night(cs, ce):
            return True
    return False


def _chain_covers_all_night(chain_start: datetime, chain_end: datetime) -> bool:
    """A chain covers an all-nighter iff some anchor day ``J`` exists with
    ``chain_start <= 22:00 UTC of J`` and ``chain_end >= 06:00 UTC of J+1``."""
    # The chain must span at least 8 hours: cheap reject before iterating.
    if chain_end - chain_start < timedelta(hours=8):
        return False

    # Candidate anchor days range from (chain_start.date() - 1) up to
    # chain_end.date(); any anchor outside that interval cannot match.
    first_day = chain_start.date() - timedelta(days=1)
    last_day = chain_end.date()
    day = first_day
    while day <= last_day:
        anchor_22 = datetime.combine(day, time(ALL_NIGHT_WINDOW_START_HOUR), tzinfo=timezone.utc)
        anchor_06 = datetime.combine(
            day + timedelta(days=1),
            time(ALL_NIGHT_WINDOW_END_HOUR),
            tzinfo=timezone.utc,
        )
        if chain_start <= anchor_22 and chain_end >= anchor_06:
            return True
        day += timedelta(days=1)
    return False


# ── secret_no_life ─────────────────────────────────────────────────────


async def has_24h_in_48h_window(
    db: AsyncSession, emby_user_ids: list[str]
) -> bool:
    """``True`` iff some 48h-wide sliding window contains 24h of viewing.

    The window is anchored on each session start and extends forward by
    ``NO_LIFE_WINDOW``; durations of all sessions starting within that
    window are summed. Two-pointer sweep over the time-sorted session
    list keeps the algorithm O(n).
    """
    sessions = await _load_user_sessions(db, emby_user_ids)
    if not sessions:
        return False

    durations = [(start, (end - start).total_seconds()) for start, end in sessions]

    right = 0
    running_total = 0.0
    n = len(durations)
    for left in range(n):
        anchor = durations[left][0]
        if right < left:
            right = left
            running_total = 0.0
        # Advance right pointer as long as right-session start is within window.
        while right < n and durations[right][0] - anchor <= NO_LIFE_WINDOW:
            running_total += durations[right][1]
            right += 1
            if running_total >= NO_LIFE_TARGET_SECONDS:
                return True
        # Slide left pointer: shrink running total by the dropped session.
        running_total -= durations[left][1]
    return False


# ── secret_king ────────────────────────────────────────────────────────


async def has_12_consecutive_top1_months(
    db: AsyncSession, emby_user_ids: list[str]
) -> bool:
    """``True`` iff the observed user holds the monthly #1 spot for at
    least 12 consecutive *qualifying* months.

    A month qualifies iff ``>= 2`` distinct Emby users have at least one
    session starting in that month (anti-trivial guard). Months that do
    not qualify are skipped — they neither count toward nor break the
    consecutive chain. A qualifying month where the strict #1 is in
    ``emby_user_ids`` adds 1 to the running streak; a qualifying month
    where it is not breaks the streak back to 0. Ties at the top are not
    counted as #1 (the trophy demands a strict win).
    """
    if not emby_user_ids:
        return False

    rows = (await db.execute(
        select(PlaybackSession.user_id, PlaybackSession.started_at, PlaybackSession.ended_at)
    )).all()
    if not rows:
        return False

    # Aggregate per (year, month, user_id) → total seconds.
    monthly_totals: dict[tuple[int, int], dict[str, float]] = defaultdict(dict)
    for user_id, started_at, ended_at in rows:
        if user_id is None:
            continue
        start = _as_utc(started_at)
        if start is None:
            continue
        end = _effective_end(start, _as_utc(ended_at))
        bucket = (start.year, start.month)
        seconds = (end - start).total_seconds()
        monthly_totals[bucket][user_id] = monthly_totals[bucket].get(user_id, 0.0) + seconds

    if not monthly_totals:
        return False

    observed = set(emby_user_ids)
    months_sorted = sorted(monthly_totals.keys())
    streak = 0
    for ym in months_sorted:
        per_user = monthly_totals[ym]
        if len(per_user) < KING_MIN_DISTINCT_USERS_PER_MONTH:
            # Month is not eligible; skip without breaking the streak.
            continue
        ranked = sorted(per_user.items(), key=lambda kv: kv[1], reverse=True)
        top_user, top_seconds = ranked[0]
        runner_seconds = ranked[1][1]
        if top_seconds <= runner_seconds:
            # Strict #1 required; tie at the top does not satisfy the trophy.
            streak = 0
            continue
        if top_user in observed:
            streak += 1
            if streak >= KING_REQUIRED_CONSECUTIVE_MONTHS:
                return True
        else:
            streak = 0
    return False
