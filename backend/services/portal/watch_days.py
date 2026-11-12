"""The days something was watched on, on the clock of the instance: what a day streak counts.

A day counts as soon as it holds watched time, whenever the title started: a film finished
after midnight fills the new day too. The time is the measured one (``watched_by_hour``),
so music, pauses and a play that never moved fill no day.
"""
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime, tzinfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import WATCH_HOUR_KEY_FORMAT
from models.playback_stats import PlaybackSession
from services.instance_time import to_local


def watch_days(watched_by_hour: Iterable[Mapping[str, int] | None], zone: tzinfo) -> set[date]:
    """The days of ``zone`` holding watched seconds, from the ``watched_by_hour`` of plays.

    An hour goes to the day it starts in: in a zone off by half an hour, the half
    past midnight stays with the day before.
    """
    hours = {hour for watched in watched_by_hour if watched for hour in watched}
    return {
        to_local(datetime.strptime(hour, WATCH_HOUR_KEY_FORMAT).replace(tzinfo=UTC), zone).date()
        for hour in hours
    }


async def load_watch_days(db: AsyncSession, filters: Iterable, zone: tzinfo) -> set[date]:
    """``watch_days`` of the plays matching ``filters``."""
    result = await db.execute(select(PlaybackSession.watched_by_hour).where(*filters))
    return watch_days(result.scalars(), zone)
