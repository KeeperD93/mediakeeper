"""Playback statistics (top movies, series, users, languages, genres)."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, distinct, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession

from ._helpers import _get_library_name_map, _normalize_library_name, _merge_by_name, _lang_display
from .exclusions import _get_exclusion_filters


async def get_playback_stats(db: AsyncSession, days: int = 30):
    """Statistiques de playback sur les N lasts jours. days=0 → tout l'history."""
    since = datetime.now(timezone.utc) - timedelta(days=days) if days > 0 else None
    exc_filters = await _get_exclusion_filters(db)

    def _apply_exc(q):
        for f in exc_filters:
            q = q.where(f)
        return q

    def _since_filter():
        if since is not None:
            return PlaybackSession.started_at >= since
        return True

    top_movies_q = await db.execute(_apply_exc(
        select(
            PlaybackSession.item_name,
            PlaybackSession.item_id,
            func.count(PlaybackSession.id).label("play_count"),
            func.count(distinct(PlaybackSession.user_id)).label("user_count"),
        ).where(
            PlaybackSession.item_type == "Movie",
            _since_filter(),
        ).group_by(
            PlaybackSession.item_name, PlaybackSession.item_id
        ).order_by(desc("play_count")).limit(5)
    ))
    top_movies = [{"name": r[0], "item_id": r[1], "plays": r[2], "users": r[3]} for r in top_movies_q.all()]

    popular_movies_q = await db.execute(_apply_exc(
        select(
            PlaybackSession.item_name, PlaybackSession.item_id,
            func.count(distinct(PlaybackSession.user_id)).label("user_count"),
            func.count(PlaybackSession.id).label("play_count"),
        ).where(PlaybackSession.item_type == "Movie", _since_filter(),
        ).group_by(PlaybackSession.item_name, PlaybackSession.item_id).order_by(desc("user_count")).limit(5)
    ))
    popular_movies = [{"name": r[0], "item_id": r[1], "users": r[2], "plays": r[3]} for r in popular_movies_q.all()]

    top_series_q = await db.execute(_apply_exc(
        select(PlaybackSession.series_name, func.count(PlaybackSession.id).label("play_count"),
            func.count(distinct(PlaybackSession.user_id)).label("user_count"),
        ).where(PlaybackSession.item_type == "Episode", PlaybackSession.series_name.isnot(None), _since_filter(),
        ).group_by(PlaybackSession.series_name).order_by(desc("play_count")).limit(5)
    ))
    top_series = [{"name": r[0], "plays": r[1], "users": r[2]} for r in top_series_q.all()]

    popular_series_q = await db.execute(_apply_exc(
        select(PlaybackSession.series_name,
            func.count(distinct(PlaybackSession.user_id)).label("user_count"),
            func.count(PlaybackSession.id).label("play_count"),
        ).where(PlaybackSession.item_type == "Episode", PlaybackSession.series_name.isnot(None), _since_filter(),
        ).group_by(PlaybackSession.series_name).order_by(desc("user_count")).limit(5)
    ))
    popular_series = [{"name": r[0], "users": r[1], "plays": r[2]} for r in popular_series_q.all()]

    by_library_q = await db.execute(_apply_exc(
        select(PlaybackSession.library_name, func.count(PlaybackSession.id).label("play_count"),
        ).where(PlaybackSession.library_name.isnot(None), _since_filter(),
        ).group_by(PlaybackSession.library_name).order_by(desc("play_count"))
    ))
    lib_map = await _get_library_name_map(db)
    by_library_raw = [{"name": _normalize_library_name(r[0], lib_map), "plays": r[1]} for r in by_library_q.all()]
    by_library = _merge_by_name(by_library_raw)

    by_client_q = await db.execute(_apply_exc(
        select(PlaybackSession.client_name, func.count(PlaybackSession.id).label("play_count"),
        ).where(_since_filter(),
        ).group_by(PlaybackSession.client_name).order_by(desc("play_count")).limit(5)
    ))
    by_client = [{"name": r[0], "plays": r[1]} for r in by_client_q.all()]

    async def _resolve_names(user_ids: list[str]) -> dict[str, str]:
        """Return the most recent user_name for each user_id."""
        if not user_ids:
            return {}
        latest_sub = (
            select(
                PlaybackSession.user_id,
                func.max(PlaybackSession.id).label("max_id"),
            )
            .where(PlaybackSession.user_id.in_(user_ids))
            .group_by(PlaybackSession.user_id)
            .subquery()
        )
        q = await db.execute(
            select(PlaybackSession.user_id, PlaybackSession.user_name)
            .join(latest_sub, (PlaybackSession.user_id == latest_sub.c.user_id) & (PlaybackSession.id == latest_sub.c.max_id))
        )
        return {r[0]: r[1] for r in q.all()}

    top_users_q = await db.execute(_apply_exc(
        select(PlaybackSession.user_id,
            func.count(PlaybackSession.id).label("play_count"),
        ).where(_since_filter(),
        ).group_by(PlaybackSession.user_id).order_by(desc("play_count")).limit(5)
    ))
    top_users_raw = [{"user_id": r[0], "plays": r[1]} for r in top_users_q.all()]
    names = await _resolve_names([u["user_id"] for u in top_users_raw])
    top_users = [{"name": names.get(u["user_id"], u["user_id"]), **u} for u in top_users_raw]

    top_users_hours_q = await db.execute(_apply_exc(
        select(PlaybackSession.user_id,
            func.sum(PlaybackSession.position_ticks).label("total_ticks"),
        ).group_by(PlaybackSession.user_id).order_by(desc("total_ticks")).limit(5)
    ))
    top_users_hours_raw = [{"user_id": r[0], "ticks": r[1] or 0} for r in top_users_hours_q.all()]
    names_h = await _resolve_names([u["user_id"] for u in top_users_hours_raw])
    top_users_hours = [{"name": names_h.get(u["user_id"], u["user_id"]), **u} for u in top_users_hours_raw]

    by_method_q = await db.execute(_apply_exc(
        select(PlaybackSession.play_method, func.count(PlaybackSession.id).label("count"),
        ).where(_since_filter(),
        ).group_by(PlaybackSession.play_method)
    ))
    by_method = [{"method": r[0] or "Unknown", "count": r[1]} for r in by_method_q.all()]

    top_transcode_q = await db.execute(_apply_exc(
        select(PlaybackSession.user_name, PlaybackSession.user_id,
            func.count(PlaybackSession.id).label("tc"),
        ).where(
            _since_filter(),
            PlaybackSession.play_method == "Transcode",
        ).group_by(PlaybackSession.user_name, PlaybackSession.user_id).order_by(desc("tc")).limit(5)
    ))
    top_transcode_users = [{"name": r[0], "user_id": r[1], "plays": r[2]} for r in top_transcode_q.all()]

    by_audio_lang_q = await db.execute(_apply_exc(
        select(PlaybackSession.audio_codec, func.count(PlaybackSession.id).label("c"),
        ).where(
            _since_filter(),
            PlaybackSession.audio_codec.isnot(None),
        ).group_by(PlaybackSession.audio_codec).order_by(desc("c")).limit(8)
    ))
    by_audio_codec = [{"name": r[0], "plays": r[1]} for r in by_audio_lang_q.all()]

    by_audio_language = []
    try:
        by_lang_q = await db.execute(_apply_exc(
            select(PlaybackSession.audio_language, func.count(PlaybackSession.id).label("c"),
            ).where(
                _since_filter(),
                PlaybackSession.audio_language.isnot(None),
                PlaybackSession.audio_language != "",
            ).group_by(PlaybackSession.audio_language).order_by(desc("c")).limit(8)
        ))
        by_audio_language = [{"name": _lang_display(r[0]), "code": r[0], "plays": r[1]} for r in by_lang_q.all()]
    except Exception:
        await db.rollback()

    total_plays_res = await db.execute(_apply_exc(
        select(func.count(PlaybackSession.id)).where(_since_filter())
    ))
    total_duration_res = await db.execute(_apply_exc(
        select(func.sum(PlaybackSession.position_ticks)).where(_since_filter())
    ))
    active_users_res = await db.execute(_apply_exc(
        select(func.count(distinct(PlaybackSession.user_id))).where(_since_filter())
    ))

    total_plays = total_plays_res.scalar() or 0
    total_duration_ticks = total_duration_res.scalar() or 0
    active_users = active_users_res.scalar() or 0

    transcode_count = sum(m["count"] for m in by_method if m["method"] == "Transcode")
    transcode_pct = round((transcode_count / total_plays * 100), 1) if total_plays > 0 else 0

    by_genre = []
    try:
        genre_q = await db.execute(_apply_exc(
            select(PlaybackSession.genres, func.count(PlaybackSession.id).label("c"),
            ).where(_since_filter(), PlaybackSession.genres.isnot(None), PlaybackSession.genres != "",
            ).group_by(PlaybackSession.genres)
        ))
        genre_counts = {}
        for row in genre_q.all():
            for g in (row[0] or "").split(","):
                g = g.strip()
                if g:
                    genre_counts[g] = genre_counts.get(g, 0) + row[1]
        by_genre = sorted([{"name": k, "plays": v} for k, v in genre_counts.items()], key=lambda x: x["plays"], reverse=True)[:15]
    except Exception:
        try:
            await db.rollback()
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass

    return {
        "period_days": days,
        "total_plays": total_plays,
        "total_duration_ticks": total_duration_ticks,
        "active_users": active_users,
        "transcode_pct": transcode_pct,
        "top_movies": top_movies,
        "popular_movies": popular_movies,
        "top_series": top_series,
        "popular_series": popular_series,
        "by_library": by_library,
        "by_client": by_client,
        "top_users": top_users,
        "top_users_hours": top_users_hours,
        "top_transcode_users": top_transcode_users,
        "by_audio_codec": by_audio_codec,
        "by_audio_language": by_audio_language,
        "by_method": by_method,
        "by_genre": by_genre,
    }
