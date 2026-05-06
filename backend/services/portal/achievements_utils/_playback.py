"""Aggregators sur PlaybackSession : marathons, weekends, season binges, etc."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.playback_stats import PlaybackSession, PlaybackPauseEvent


async def _resolve_playback_user_names(
    db: AsyncSession, user_id: int, user_name: str | None
) -> list[str]:
    """Resolve the candidate user_name strings used to match Emby rows.

    Returns the deduplicated list of non-empty names that may identify
    the user across the Emby integration: explicit override, MK
    ``users.username``, and ``user_profiles.display_name``.
    """
    from models.user import User

    profile = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )).scalar_one_or_none()
    user_obj = await db.get(User, user_id)

    names: list[str] = []
    for candidate in (
        user_name,
        user_obj.username if user_obj else None,
        profile.display_name if profile else None,
    ):
        candidate = (candidate or "").strip()
        if candidate and candidate not in names:
            names.append(candidate)
    return names


async def _build_playback_user_filter(
    db: AsyncSession, user_id: int, user_name: str | None
):
    names = await _resolve_playback_user_names(db, user_id, user_name)
    if not names:
        return None
    return PlaybackSession.user_name.in_(names)


async def _build_pause_user_filter(
    db: AsyncSession, user_id: int, user_name: str | None
):
    names = await _resolve_playback_user_names(db, user_id, user_name)
    if not names:
        return None
    return PlaybackPauseEvent.user_name.in_(names)


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _session_duration_seconds(row: PlaybackSession) -> int:
    """Best-effort estimate of how long the user actually watched.

    Three signals available, ranked by reliability:
      - ``position_ticks``: absolute position inside the media; bounds the
        real watch time from above (a paused session can't have advanced
        the position). Trustworthy when non-zero.
      - ``runtime_ticks``: media duration; a single session can't watch
        more than this regardless of how long it stayed open.
      - wall clock (``ended_at - started_at``): inflated by long pauses
        or by stale sessions closed late by the collector.

    We take the wall clock and clamp it down with whichever upper bound
    is tighter — anti-cheat for the marathon trophies."""
    started = _coerce_utc(row.started_at)
    ended = _coerce_utc(row.ended_at) or _coerce_utc(row.last_seen_at)
    wall = int((ended - started).total_seconds()) if (
        started and ended and ended >= started
    ) else 0

    position_seconds = int((row.position_ticks or 0) / 10_000_000)
    runtime_seconds = int((row.duration_ticks or 0) / 10_000_000)

    candidates = [c for c in (wall, position_seconds, runtime_seconds) if c > 0]
    if not candidates:
        return 0
    return min(candidates)


def _count_marathon_days(rows: list[PlaybackSession]) -> int:
    by_day: dict[date, int] = defaultdict(int)
    for row in rows:
        started = _coerce_utc(row.started_at)
        if not started:
            continue
        by_day[started.date()] += _session_duration_seconds(row)
    return sum(1 for seconds in by_day.values() if seconds >= 8 * 3600)


def _count_max_weekend_plays(rows: list[PlaybackSession]) -> int:
    by_weekend: dict[date, int] = defaultdict(int)
    for row in rows:
        started = _coerce_utc(row.started_at)
        if not started:
            continue
        weekday = started.weekday()
        if weekday not in (5, 6):
            continue
        weekend_start = started.date() if weekday == 5 else started.date() - timedelta(days=1)
        by_weekend[weekend_start] += 1
    return max(by_weekend.values(), default=0)


def _count_season_binges(rows: list[PlaybackSession]) -> int:
    windows = defaultdict(list)
    for row in rows:
        started = _coerce_utc(row.started_at)
        if (
            row.item_type != "Episode"
            or not row.series_name
            or row.season_number is None
            or row.episode_number is None
            or started is None
        ):
            continue
        windows[(row.series_name, row.season_number)].append((started, row.episode_number))

    binge_count = 0
    span = timedelta(hours=24)
    for episodes in windows.values():
        episodes.sort(key=lambda item: item[0])
        counts: dict[int, int] = defaultdict(int)
        left = 0
        for right, (ts, episode_number) in enumerate(episodes):
            counts[episode_number] += 1
            while ts - episodes[left][0] > span:
                left_episode = episodes[left][1]
                counts[left_episode] -= 1
                if counts[left_episode] <= 0:
                    counts.pop(left_episode, None)
                left += 1

            if len(counts) < 3:
                continue

            numbers = sorted(counts)
            if numbers[0] == 1 and numbers[-1] == len(numbers):
                binge_count += 1
                break

    return binge_count


def _normalize_library_name(name: str | None) -> str:
    return (name or "").strip().casefold()
