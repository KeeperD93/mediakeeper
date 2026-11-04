"""Charts: daily data and weekly heatmap, on the clock of the instance.

Rows are grouped here and not in SQL, which only knows the zone of its session.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import TICKS_PER_SECOND
from models.playback_stats import PlaybackSession
from services.instance_time import get_instance_zone, to_local

from ._helpers import _apply_filters, _get_library_name_map, _normalize_library_name
from .exclusions import _get_exclusion_filters


async def get_daily_chart_data(db: AsyncSession, days: int = 30, group_by: str = "library"):
    """
    Data for daily activity charts.
    group_by: "library" ou "user"
    """
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    exc_filters = await _get_exclusion_filters(db)
    zone = await get_instance_zone(db)

    # Per user: their watch time (video, concurrent devices once); per
    # library: the time spent on its titles, music included.
    if group_by == "user":
        group_col = PlaybackSession.user_name
        seconds_col = PlaybackSession.exclusive_seconds
    else:
        group_col = PlaybackSession.library_name
        seconds_col = PlaybackSession.watched_seconds

    base_q = select(
            PlaybackSession.started_at,
            group_col.label("group_name"),
            seconds_col.label("seconds"),
        ).where(
            PlaybackSession.started_at >= since,
            group_col.isnot(None),
        )

    q = await db.execute(_apply_filters(base_q, exc_filters))
    rows = q.all()

    lib_map = {}
    if group_by == "library":
        lib_map = await _get_library_name_map(db)

    data = {}
    groups = set()
    for started_at, raw_name, seconds in rows:
        day_str = to_local(started_at, zone).date().isoformat()
        group_name = _normalize_library_name(raw_name, lib_map) if lib_map else raw_name
        groups.add(group_name)
        totals = data.setdefault(day_str, {}).setdefault(group_name, {"count": 0, "duration": 0})
        totals["count"] += 1
        totals["duration"] += (seconds or 0) * TICKS_PER_SECOND

    all_days = []
    current = to_local(since, zone).date()
    end = to_local(now, zone).date()
    while current <= end:
        day_str = str(current)
        all_days.append(day_str)
        if day_str not in data:
            data[day_str] = {}
        current += timedelta(days=1)

    return {
        "days": all_days,
        "groups": sorted(groups),
        "data": data,
    }


async def get_weekly_heatmap(db: AsyncSession, days: int = 90):
    """Heatmap jour/heure des playbacks sur les N lasts jours."""
    since = datetime.now(UTC) - timedelta(days=days)
    exc_filters = await _get_exclusion_filters(db)
    zone = await get_instance_zone(db)

    q = await db.execute(
        _apply_filters(
            select(PlaybackSession.started_at).where(PlaybackSession.started_at >= since),
            exc_filters,
        )
    )

    grid = [[0] * 24 for _ in range(7)]
    for started_at in q.scalars():
        local = to_local(started_at, zone)
        # Sunday first, like the labels below.
        grid[local.isoweekday() % 7][local.hour] += 1

    return {
        "grid": grid,
        "days": ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"],
        "period_days": days,
    }
