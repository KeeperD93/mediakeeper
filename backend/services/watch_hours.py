"""Watched seconds per UTC hour, as a play keeps them in ``watched_by_hour``.

Shared by the collector, which writes them, and the day streaks, which read them; free of
both so neither imports the other.
"""
from datetime import UTC, datetime, timedelta

from constants.playback import WATCH_HOUR_KEY_FORMAT
from services.instance_time import to_local


def spread_over_hours(start: datetime, seconds: int) -> dict[str, int]:
    """Lay ``seconds`` contiguously from ``start``, per UTC hour: used when only
    the played duration is known (imported history), not the real timeline."""
    buckets: dict[str, int] = {}
    cursor, left = to_local(start, UTC), seconds
    while left > 0:
        next_hour = cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        chunk = min(left, int((next_hour - cursor).total_seconds()) or 1)
        key = cursor.strftime(WATCH_HOUR_KEY_FORMAT)
        buckets[key] = buckets.get(key, 0) + chunk
        left -= chunk
        cursor = next_hour
    return buckets


def hour_start(key: str) -> datetime:
    """The UTC moment a ``watched_by_hour`` key starts at."""
    return datetime.strptime(key, WATCH_HOUR_KEY_FORMAT).replace(tzinfo=UTC)
