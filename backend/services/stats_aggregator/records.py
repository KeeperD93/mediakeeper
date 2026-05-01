"""Records, streaks et faits marquants for les stat cards."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

from .exclusions import _get_exclusion_filters


async def get_records(db: AsyncSession):
    """Records, streaks et faits marquants for les stat cards."""
    exc_filters = await _get_exclusion_filters(db)

    # Record jour (plus de playbacks en 1 jour)
    day_q = select(
        func.date(PlaybackSession.started_at).label("day"),
        func.count(PlaybackSession.id).label("count"),
    ).group_by("day").order_by(desc("count")).limit(1)
    for f in exc_filters:
        day_q = day_q.where(f)
    record_day_res = await db.execute(day_q)
    record_day = record_day_res.first()

    # Streak (consecutive days with at least 1 playback)
    all_days_q = select(
        func.date(PlaybackSession.started_at).label("day"),
    ).distinct().order_by(desc("day"))
    for f in exc_filters:
        all_days_q = all_days_q.where(f)
    all_days_res = await db.execute(all_days_q)
    play_dates = [r[0] for r in all_days_res.all()]

    current_streak = 0
    longest_streak = 0
    if play_dates:
        today = datetime.now(timezone.utc).date()
        streak = 0
        check = today
        for d in play_dates:
            if d == check:
                streak += 1
                check -= timedelta(days=1)
            elif d < check:
                break
        current_streak = streak

        if len(play_dates) > 0:
            best = 1
            run = 1
            sorted_dates = sorted(set(play_dates))
            for i in range(1, len(sorted_dates)):
                if sorted_dates[i] - sorted_dates[i-1] == timedelta(days=1):
                    run += 1
                    best = max(best, run)
                else:
                    run = 1
            longest_streak = best

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

    # Heure la plus active
    hour_q = select(
        func.extract("hour", PlaybackSession.started_at).label("hour"),
        func.count(PlaybackSession.id).label("cnt"),
    ).group_by("hour").order_by(desc("cnt")).limit(1)
    for f in exc_filters:
        hour_q = hour_q.where(f)
    hour_res = await db.execute(hour_q)
    peak_hour_row = hour_res.first()

    return {
        "record_day_date": str(record_day[0]) if record_day else None,
        "record_day_count": record_day[1] if record_day else 0,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "top_user_name": top_user_name,
        "top_user_pct": top_user_pct,
        "peak_hour": int(peak_hour_row[0]) if peak_hour_row else None,
        "peak_hour_count": peak_hour_row[1] if peak_hour_row else 0,
    }
