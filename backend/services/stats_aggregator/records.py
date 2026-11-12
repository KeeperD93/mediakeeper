"""Records, streaks et faits marquants for les stat cards."""
import asyncio
from collections import Counter
from datetime import UTC, date, datetime, tzinfo

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from services.instance_time import get_instance_zone, to_local
from services.portal.play_streak import current_streak, longest_streak, most_played
from services.portal.watch_days import WATCH_DAY_COLUMNS, watch_days

from ._helpers import _apply_filters
from .exclusions import _get_exclusion_filters


def _count_days_and_hours(plays: list, zone: tzinfo) -> tuple[Counter[date], Counter[int], set[date]]:
    """Plays per day and per hour of their start, and the days watched, on the clock of ``zone``."""
    starts = [to_local(play.started_at, zone) for play in plays if play.started_at]
    plays_per_day = Counter(start.date() for start in starts)
    plays_per_hour = Counter(start.hour for start in starts)
    return plays_per_day, plays_per_hour, watch_days(plays, zone)


async def get_records(db: AsyncSession):
    """Records, streaks et faits marquants for les stat cards."""
    exc_filters = await _get_exclusion_filters(db)
    zone = await get_instance_zone(db)

    # Days and hours on the clock of the instance: SQL only knows its session's zone.
    # One read serves the start of each play and the days watched; counting every play
    # of the instance runs off the event loop.
    plays = (await db.execute(_apply_filters(select(*WATCH_DAY_COLUMNS), exc_filters))).all()
    plays_per_day, plays_per_hour, watched_days = await asyncio.to_thread(_count_days_and_hours, plays, zone)
    record_day = most_played(plays_per_day) if plays_per_day else None
    peak_hour = most_played(plays_per_hour) if plays_per_hour else None
    today = to_local(datetime.now(UTC), zone).date()

    # Top user percentage
    top_user_q = select(
        PlaybackSession.user_name,
        func.count(PlaybackSession.id).label("cnt"),
    ).group_by(PlaybackSession.user_name).order_by(desc("cnt")).limit(1)
    for f in exc_filters:
        top_user_q = top_user_q.where(f)
    top_user_res = await db.execute(top_user_q)
    top_user_row = top_user_res.first()

    total_q = select(func.count(PlaybackSession.id))
    for f in exc_filters:
        total_q = total_q.where(f)
    total_res = await db.execute(total_q)
    total_plays = total_res.scalar() or 0

    top_user_name = top_user_row[0] if top_user_row else None
    top_user_pct = round((top_user_row[1] / total_plays * 100), 1) if top_user_row and total_plays > 0 else 0

    return {
        "record_day_date": record_day.isoformat() if record_day else None,
        "record_day_count": plays_per_day[record_day],
        "current_streak": current_streak(watched_days, today),
        "longest_streak": longest_streak(watched_days),
        "top_user_name": top_user_name,
        "top_user_pct": top_user_pct,
        "peak_hour": peak_hour,
        "peak_hour_count": plays_per_hour[peak_hour],
    }
