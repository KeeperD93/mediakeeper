"""Charts: daily data and weekly heatmap."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

from ._helpers import _apply_filters, _get_library_name_map, _normalize_library_name
from .exclusions import _get_exclusion_filters


async def get_daily_chart_data(db: AsyncSession, days: int = 30, group_by: str = "library"):
    """
    Data for daily activity charts.
    group_by: "library" ou "user"
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    exc_filters = await _get_exclusion_filters(db)

    if group_by == "user":
        group_col = PlaybackSession.user_name
    else:
        group_col = PlaybackSession.library_name

    base_q = select(
            func.date(PlaybackSession.started_at).label("day"),
            group_col.label("group_name"),
            func.count(PlaybackSession.id).label("count"),
            func.sum(PlaybackSession.position_ticks).label("duration"),
        ).where(
            PlaybackSession.started_at >= since,
            group_col.isnot(None),
        ).group_by("day", "group_name").order_by("day")

    for f in exc_filters:
        base_q = base_q.where(f)

    q = await db.execute(base_q)
    rows = q.all()

    lib_map = {}
    if group_by == "library":
        lib_map = await _get_library_name_map(db)

    data = {}
    groups = set()
    for r in rows:
        day_str = str(r[0])
        group_name = _normalize_library_name(r[1], lib_map) if lib_map else r[1]
        groups.add(group_name)
        if day_str not in data:
            data[day_str] = {}
        if group_name in data[day_str]:
            data[day_str][group_name]["count"] += r[2]
            data[day_str][group_name]["duration"] += (r[3] or 0)
        else:
            data[day_str][group_name] = {
                "count": r[2],
                "duration": r[3] or 0,
            }

    all_days = []
    current = since.date()
    end = datetime.now(timezone.utc).date()
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
    since = datetime.now(timezone.utc) - timedelta(days=days)
    exc_filters = await _get_exclusion_filters(db)

    q = await db.execute(
        _apply_filters(
            select(
                func.extract("dow", PlaybackSession.started_at).label("dow"),
                func.extract("hour", PlaybackSession.started_at).label("hour"),
                func.count(PlaybackSession.id).label("count"),
            ).where(
                PlaybackSession.started_at >= since,
            ).group_by("dow", "hour"),
            exc_filters,
        )
    )

    grid = [[0] * 24 for _ in range(7)]
    for r in q.all():
        dow = int(r[0])
        hour = int(r[1])
        grid[dow][hour] = r[2]

    return {
        "grid": grid,
        "days": ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"],
        "period_days": days,
    }
