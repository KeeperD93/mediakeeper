"""Helpers over PlaybackSession: user filters, watch time, season binges."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import WATCH_ITEM_TYPES
from models.playback_stats import PlaybackPauseEvent, PlaybackSession
from models.portal.profile import UserProfile
from models.user import User
from services.portal.playback_owner import played_by


async def _player_identity(db: AsyncSession, user_id: int) -> tuple[str | None, str | None]:
    """The Emby id and the login :func:`played_by` needs, ``(None, None)`` for no account."""
    row = (await db.execute(
        select(UserProfile.emby_user_id, User.username)
        .select_from(User)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .where(User.id == user_id)
    )).first()
    return (row.emby_user_id, row.username) if row else (None, None)


async def _build_playback_user_filter(db: AsyncSession, user_id: int):
    return played_by(PlaybackSession, *await _player_identity(db, user_id))


async def _build_pause_user_filter(db: AsyncSession, user_id: int):
    return played_by(PlaybackPauseEvent, *await _player_identity(db, user_id))


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _session_duration_seconds(row: PlaybackSession) -> int:
    """Seconds of this session that count as the user's watch time.

    The collector measures it at every poll (``exclusive_seconds``: video
    only, concurrent devices counted once); history rows carry the estimate
    stored by migration 062 or by the import. A row with nothing stored falls
    back to that same estimate."""
    if row.measured or row.watched_seconds or row.exclusive_seconds:
        return row.exclusive_seconds or 0
    if row.item_type not in WATCH_ITEM_TYPES:
        return 0
    return _estimated_seconds(row)


def _estimated_seconds(row: PlaybackSession) -> int:
    """Best-effort estimate when no measurement exists.

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
