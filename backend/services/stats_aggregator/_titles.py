"""Title rankings of the Statistics cards: most watched and popular titles.

Most watched = the time actually spent on a title, by every viewer and in
every sitting, finished or not. Popular = the number of different people who
watched it past the watch threshold; on a tie the most recently watched comes
first, so the two lists do not mirror each other in a small community.
"""
from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import TICKS_PER_SECOND
from models.playback_stats import PlaybackSession
from services.portal._watch_threshold import watched_session_filter

RANK_LIMIT = 5


async def title_rankings(db: AsyncSession, filters: list) -> dict:
    """The four title cards; ``filters`` holds the exclusions and the period."""
    movie = (PlaybackSession.item_type == "Movie",)
    episode = (PlaybackSession.item_type == "Episode", PlaybackSession.series_name.isnot(None))
    seconds = func.sum(PlaybackSession.watched_seconds)
    viewers = func.count(distinct(PlaybackSession.user_id))
    last_watched = func.max(PlaybackSession.started_at)

    async def most_watched(*keys, where):
        q = (
            select(*keys, seconds.label("seconds"))
            .where(*where, *filters)
            .group_by(*keys)
            .having(seconds > 0)
            .order_by(desc("seconds"), keys[0])
            .limit(RANK_LIMIT)
        )
        return (await db.execute(q)).all()

    async def popular(*keys, where):
        q = (
            select(*keys, viewers.label("viewers"))
            .where(*where, watched_session_filter(), *filters)
            .group_by(*keys)
            .order_by(desc("viewers"), desc(last_watched), keys[0])
            .limit(RANK_LIMIT)
        )
        return (await db.execute(q)).all()

    movie_keys = (PlaybackSession.item_name, PlaybackSession.item_id)
    top_movies = await most_watched(*movie_keys, where=movie)
    popular_movies = await popular(*movie_keys, where=movie)
    top_series = await most_watched(PlaybackSession.series_name, where=episode)
    popular_series = await popular(PlaybackSession.series_name, where=episode)

    return {
        "top_movies": [
            {"name": r.item_name, "item_id": r.item_id, "ticks": r.seconds * TICKS_PER_SECOND}
            for r in top_movies
        ],
        "popular_movies": [
            {"name": r.item_name, "item_id": r.item_id, "users": r.viewers} for r in popular_movies
        ],
        "top_series": [
            {"name": r.series_name, "ticks": r.seconds * TICKS_PER_SECOND} for r in top_series
        ],
        "popular_series": [{"name": r.series_name, "users": r.viewers} for r in popular_series],
    }
