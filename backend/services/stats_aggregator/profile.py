"""Detailed user profile."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

from ._helpers import _get_library_name_map, _normalize_library_name, _merge_by_name
from .exclusions import _get_exclusion_filters


async def get_user_profile(db: AsyncSession, user_id: str):
    """Detailed user profile: stats, top movies/series, 30-day activity."""
    exc_filters = await _get_exclusion_filters(db)

    base_where = [PlaybackSession.user_id == user_id] + exc_filters

    play_q = select(func.count(PlaybackSession.id)).where(*base_where)
    play_res = await db.execute(play_q)
    play_count = play_res.scalar() or 0

    dur_q = select(func.sum(PlaybackSession.position_ticks)).where(*base_where)
    dur_res = await db.execute(dur_q)
    total_ticks = dur_res.scalar() or 0

    last_q = select(
        PlaybackSession.item_name,
        PlaybackSession.series_name,
        PlaybackSession.last_seen_at,
        PlaybackSession.device_name,
        PlaybackSession.client_name,
    ).where(*base_where).order_by(desc(PlaybackSession.last_seen_at)).limit(1)
    last_res = await db.execute(last_q)
    last_row = last_res.first()

    movies_q = select(
        PlaybackSession.item_name.label("name"),
        PlaybackSession.item_id.label("item_id"),
        func.count(PlaybackSession.id).label("plays"),
    ).where(
        *base_where,
        PlaybackSession.item_type == "Movie",
    ).group_by(PlaybackSession.item_name, PlaybackSession.item_id).order_by(desc("plays")).limit(5)
    movies_res = await db.execute(movies_q)
    top_movies = [{"name": r[0], "item_id": r[1], "plays": r[2]} for r in movies_res.all()]

    series_q = select(
        PlaybackSession.series_name.label("name"),
        func.count(PlaybackSession.id).label("plays"),
    ).where(
        *base_where,
        PlaybackSession.series_name.isnot(None),
        PlaybackSession.series_name != "",
    ).group_by(PlaybackSession.series_name).order_by(desc("plays")).limit(5)
    series_res = await db.execute(series_q)
    top_series = [{"name": r[0], "plays": r[1]} for r in series_res.all()]

    since = datetime.now(timezone.utc) - timedelta(days=30)
    daily_q = select(
        func.date(PlaybackSession.started_at).label("day"),
        func.count(PlaybackSession.id).label("count"),
    ).where(
        *base_where,
        PlaybackSession.started_at >= since,
    ).group_by("day").order_by("day")
    daily_res = await db.execute(daily_q)
    daily_map = {}
    for r in daily_res.all():
        if r[0]:
            daily_map[str(r[0])] = r[1]

    daily = []
    for i in range(30):
        d = (datetime.now(timezone.utc) - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        daily.append({"date": d, "count": daily_map.get(d, 0)})

    method_q = select(
        PlaybackSession.play_method.label("method"),
        func.count(PlaybackSession.id).label("count"),
    ).where(*base_where).group_by(PlaybackSession.play_method).order_by(desc("count"))
    method_res = await db.execute(method_q)
    by_method = [{"method": r[0] or "Unknown", "count": r[1]} for r in method_res.all()]

    type_q = select(
        PlaybackSession.item_type.label("type"),
        func.count(PlaybackSession.id).label("count"),
    ).where(*base_where).group_by(PlaybackSession.item_type).order_by(desc("count"))
    type_res = await db.execute(type_q)
    by_content_type = [{"type": r[0] or "Autre", "count": r[1]} for r in type_res.all()]

    lib_map = await _get_library_name_map(db)
    lib_q = select(
        PlaybackSession.library_name.label("lib"),
        func.count(PlaybackSession.id).label("count"),
    ).where(*base_where, PlaybackSession.library_name.isnot(None),
    ).group_by(PlaybackSession.library_name).order_by(desc("count")).limit(6)
    lib_res = await db.execute(lib_q)
    by_library_raw = [{"name": _normalize_library_name(r[0], lib_map), "count": r[1]} for r in lib_res.all()]
    by_library = _merge_by_name(by_library_raw, val_key="count")

    by_genre = []
    try:
        genre_q = await db.execute(
            select(PlaybackSession.genres, func.count(PlaybackSession.id).label("c"),
            ).where(*base_where, PlaybackSession.genres.isnot(None), PlaybackSession.genres != "",
            ).group_by(PlaybackSession.genres)
        )
        genre_counts = {}
        for row in genre_q.all():
            for g in (row[0] or "").split(","):
                g = g.strip()
                if g:
                    genre_counts[g] = genre_counts.get(g, 0) + row[1]
        by_genre = sorted([{"name": k, "plays": v} for k, v in genre_counts.items()], key=lambda x: x["plays"], reverse=True)[:12]
    except Exception:
        pass

    return {
        "user_id": user_id,
        "play_count": play_count,
        "total_ticks": total_ticks,
        "last_play": last_row[0] if last_row else None,
        "last_series": last_row[1] if last_row else None,
        "last_seen": last_row[2].isoformat() if last_row and last_row[2] and hasattr(last_row[2], 'isoformat') else str(last_row[2]) if last_row and last_row[2] else None,
        "last_device": last_row[3] if last_row else None,
        "last_client": last_row[4] if last_row else None,
        "top_movies": top_movies,
        "top_series": top_series,
        "daily_activity": daily,
        "by_method": by_method,
        "by_content_type": by_content_type,
        "by_library": by_library,
        "by_genre": by_genre,
    }
