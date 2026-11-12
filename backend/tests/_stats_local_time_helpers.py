"""Plays and a frozen clock for the tests of the admin statistics in a time zone."""
from datetime import UTC, datetime, timedelta

from models.playback_stats import PlaybackSession
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.settings import set_setting
from services.stats_aggregator import charts, profile, records
from services.stats_collector._measure import spread_over_hours

SECOND_IN_TICKS = 10_000_000


def utc(year: int, month: int, day: int, *clock: int) -> datetime:
    return datetime(year, month, day, *clock, tzinfo=UTC)


def freeze(monkeypatch, moment: datetime) -> None:
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    for module in (charts, records, profile):
        monkeypatch.setattr(module, "datetime", _Frozen)


def play(
    db, started: datetime, *, user: str = "alice", item: str = "Test Movie",
    library: str | None = "Films", watched: int = 60, exclusive: int = 30,
) -> None:
    db.add(PlaybackSession(
        session_key=f"{user}-{item}-{started.timestamp()}-{len(db.new)}",
        user_id=f"emby-{user}",
        user_name=user,
        item_id="item-1",
        item_name=item,
        item_type="Movie",
        library_name=library,
        started_at=started,
        last_seen_at=started,
        ended_at=started + timedelta(minutes=1),
        watched_seconds=watched,
        exclusive_seconds=exclusive,
        watched_by_hour=spread_over_hours(started, exclusive),
    ))


async def save_paris(db) -> None:
    await set_setting(db, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
