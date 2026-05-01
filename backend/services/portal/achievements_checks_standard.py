"""Standard (tiered) achievement checks: watching, languages, genres, community, marathon, binge."""
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement
from models.playback_stats import PlaybackSession, LibraryCache
from models.portal.chat import ChatMessage
from models.portal.request import MediaRequest
from services.portal.achievements_utils import (
    update_progress,
    _count_marathon_days,
    _count_max_weekend_plays,
    _count_season_binges,
    _normalize_library_name,
)


async def check_standard(
    db: AsyncSession,
    by_type: dict[str, list[Achievement]],
    user_id: int,
    ua_map: dict,
    unlocked_ids: set[str],
    user_filter,
    excl_filters: list,
    playback_rows: list | None,
) -> list[dict]:
    """Run all tiered checks. Returns list of newly unlocked achievement dicts."""
    unlocks: list[dict] = []

    async def _apply(cond_type: str, value: int):
        if cond_type not in by_type:
            return
        for ach in by_type[cond_type]:
            if ach.id in unlocked_ids:
                continue
            r = await update_progress(db, user_id, ach.id, new_value=value, ua_map=ua_map)
            if r:
                unlocks.append(r)

    # --- watch_movies: count distinct movies ---
    if "watch_movies" in by_type:
        val = (await db.execute(
            select(func.count(distinct(PlaybackSession.item_id)))
            .where(user_filter, PlaybackSession.item_type == "Movie", *excl_filters)
        )).scalar() or 0
        await _apply("watch_movies", val)

    # --- watch_series: count distinct series ---
    if "watch_series" in by_type:
        val = (await db.execute(
            select(func.count(distinct(PlaybackSession.series_name)))
            .where(user_filter, PlaybackSession.item_type == "Episode",
                   PlaybackSession.series_name.isnot(None), *excl_filters)
        )).scalar() or 0
        await _apply("watch_series", val)

    # --- night_watch: plays started between 00:00-05:00 ---
    if "night_watch" in by_type:
        val = (await db.execute(
            select(func.count(PlaybackSession.id))
            .where(
                user_filter, *excl_filters,
                func.extract("hour", PlaybackSession.started_at) < 5,
            )
        )).scalar() or 0
        await _apply("night_watch", val)

    # --- audio_languages: distinct audio languages ---
    if "audio_languages" in by_type:
        val = (await db.execute(
            select(func.count(distinct(PlaybackSession.audio_language)))
            .where(user_filter, PlaybackSession.audio_language.isnot(None), *excl_filters)
        )).scalar() or 0
        await _apply("audio_languages", val)

    # --- subtitle_languages: distinct subtitle languages ---
    if "subtitle_languages" in by_type:
        val = (await db.execute(
            select(func.count(distinct(PlaybackSession.subtitle_language)))
            .where(user_filter, PlaybackSession.subtitle_language.isnot(None), *excl_filters)
        )).scalar() or 0
        await _apply("subtitle_languages", val)

    # --- rewatch_count: items watched 5+ times ---
    if "rewatch_count" in by_type:
        val = (await db.execute(
            select(func.count()).select_from(
                select(PlaybackSession.item_id)
                .where(user_filter, *excl_filters)
                .group_by(PlaybackSession.item_id)
                .having(func.count(PlaybackSession.id) >= 5)
                .subquery()
            )
        )).scalar() or 0
        await _apply("rewatch_count", val)

    # --- genre_diversity: distinct comma-split genres from playback history ---
    if "genre_diversity" in by_type:
        genre_rows = (await db.execute(
            select(PlaybackSession.genres)
            .where(user_filter, PlaybackSession.genres.isnot(None), *excl_filters)
            .distinct()
        )).scalars().all()
        all_genres = set()
        for g_str in genre_rows:
            if g_str:
                for g in g_str.split(","):
                    g = g.strip()
                    if g:
                        all_genres.add(g)
        await _apply("genre_diversity", len(all_genres))

    # --- requests_created ---
    if "requests_created" in by_type:
        val = (await db.execute(
            select(func.count(MediaRequest.id))
            .where(MediaRequest.user_id == user_id)
        )).scalar() or 0
        await _apply("requests_created", val)

    # --- chat_messages ---
    if "chat_messages" in by_type:
        val = (await db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.user_id == user_id)
        )).scalar() or 0
        await _apply("chat_messages", val)

    # --- marathon_hours: days with 8h+ watched ---
    if "marathon_hours" in by_type:
        await _apply("marathon_hours", _count_marathon_days(playback_rows or []))

    # --- streak_days: handled by profile_stats streak calculation ---
    if "streak_days" in by_type:
        from services.portal.profile_stats import _compute_streak
        streak = await _compute_streak(db, user_filter, excl_filters)
        await _apply("streak_days", streak)

    # --- weekend_plays: max plays across a single Saturday+Sunday pair ---
    if "weekend_plays" in by_type:
        await _apply("weekend_plays", _count_max_weekend_plays(playback_rows or []))

    # --- season_binge: contiguous season episodes watched within 24h ---
    if "season_binge" in by_type:
        await _apply("season_binge", _count_season_binges(playback_rows or []))

    # --- library_explorer: at least one play in every known library ---
    if "library_explorer" in by_type:
        known_libraries = {
            _normalize_library_name(name)
            for name in (await db.execute(
                select(LibraryCache.name).where(LibraryCache.name.isnot(None))
            )).scalars().all()
            if _normalize_library_name(name)
        }
        watched_libraries = {
            _normalize_library_name(row.library_name)
            for row in (playback_rows or [])
            if _normalize_library_name(row.library_name)
        }
        if not known_libraries:
            known_libraries = watched_libraries
        val = 1 if known_libraries and known_libraries.issubset(watched_libraries) else 0
        await _apply("library_explorer", val)

    return unlocks
