"""Continuous watch-time measurement, one Emby poll at a time.

Each poll adds the smaller of the elapsed time and the position progress since
the previous poll: a pause, a stall or a frozen player adds nothing, a seek
forward only adds the time really spent. Emby keeps advancing the position on
its side every second, so the precision follows the polling interval.
"""
import re
from datetime import datetime, timedelta, timezone

from constants.playback import TICKS_PER_SECOND, WATCH_ITEM_TYPES

# Delay between two polls: the precision of every measured session.
POLL_INTERVAL_SECONDS = 5
# A first poll this close to the start of the title is a real start, not a
# resume: those seconds were watched before the collector saw the session.
FRESH_START_MAX_SECONDS = 15
# Emby stops refreshing ``LastActivityDate`` once the player goes silent
# (TV switched off, app killed). Past this delay the session is stalled.
CLIENT_SILENCE_LIMIT = timedelta(minutes=2)

_EXTRA_FRACTION_DIGITS = re.compile(r"(\.\d{6})\d+")


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def parse_emby_date(value: str | None) -> datetime | None:
    """Emby dates carry 7 fractional digits ("…:50.2057071Z"); Python reads 6."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(_EXTRA_FRACTION_DIGITS.sub(r"\1", value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return as_utc(parsed)


def client_is_alive(session: dict, now: datetime) -> bool:
    """False once the player has been silent for too long (unknown = alive)."""
    last_activity = parse_emby_date(session.get("LastActivityDate"))
    return last_activity is None or now - last_activity <= CLIENT_SILENCE_LIMIT


def progress_seconds(
    previous_position_ticks: int | None,
    previous_tick_at: datetime | None,
    position_ticks: int | None,
    now: datetime,
) -> int:
    """Seconds really watched since the previous poll of the same row."""
    previous_at = as_utc(previous_tick_at)
    if previous_at is None or previous_position_ticks is None:
        return 0
    elapsed = (now - previous_at).total_seconds()
    progressed = ((position_ticks or 0) - previous_position_ticks) / TICKS_PER_SECOND
    return max(0, int(min(elapsed, progressed)))


def fresh_start_seconds(position_ticks: int | None) -> int:
    """Seconds to credit when a new row is first seen near the title's start."""
    seconds = (position_ticks or 0) / TICKS_PER_SECOND
    return int(seconds) if 0 < seconds <= FRESH_START_MAX_SECONDS else 0


def add_to_hour(buckets: dict | None, at: datetime, seconds: int) -> dict | None:
    """Return a new ``{"YYYY-MM-DDTHH": seconds}`` mapping (UTC hours) with ``seconds`` added."""
    if seconds <= 0:
        return buckets
    updated = dict(buckets or {})  # a new object so the JSON column is flagged dirty
    key = as_utc(at).strftime("%Y-%m-%dT%H")
    updated[key] = updated.get(key, 0) + seconds
    return updated


def spread_over_hours(start: datetime, seconds: int) -> dict[str, int]:
    """Lay ``seconds`` contiguously from ``start``, per UTC hour: used when only
    the played duration is known (imported history), not the real timeline."""
    buckets: dict[str, int] = {}
    cursor, left = as_utc(start), seconds
    while left > 0:
        next_hour = cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        chunk = min(left, int((next_hour - cursor).total_seconds()) or 1)
        key = cursor.strftime("%Y-%m-%dT%H")
        buckets[key] = buckets.get(key, 0) + chunk
        left -= chunk
        cursor = next_hour
    return buckets


def history_measure(session_key: str, item_type: str, started_at: datetime, seconds: int) -> dict:
    """Measurement columns of a row rebuilt from history (played duration only)."""
    is_video = item_type in WATCH_ITEM_TYPES
    return {
        "emby_session_key": session_key,
        "watched_seconds": seconds,
        "exclusive_seconds": seconds if is_video else 0,
        "watched_by_hour": spread_over_hours(started_at, seconds) if is_video and seconds else None,
        "measured": False,
    }


def exclusive_shares(progress: list[tuple[object, str, int]]) -> dict[object, int]:
    """Per user, a poll counts once even when several devices play at once.

    ``progress`` holds ``(row, emby_user_id, seconds)``; the row that moved the
    most gets the user's time for this poll, the others get nothing.
    """
    best: dict[str, tuple[object, int]] = {}
    for row, user_id, seconds in progress:
        if seconds > 0 and (user_id not in best or seconds > best[user_id][1]):
            best[user_id] = (row, seconds)
    return {row: seconds for row, seconds in best.values()}
