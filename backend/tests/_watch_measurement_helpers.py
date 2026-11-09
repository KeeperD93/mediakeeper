"""Replay of Emby polls through the real collector, for the watch-time tests."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from models.playback_stats import PlaybackCompletion, PlaybackSession
from services.stats_collector._player_reports import StoredPosition
from services.stats_collector.collect import collect_active_sessions

TICK = 10_000_000
T0 = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)
STEP = timedelta(seconds=5)


def _emby_date(at: datetime) -> str:
    # Emby writes 7 fractional digits and a trailing Z.
    return at.strftime("%Y-%m-%dT%H:%M:%S.%f") + "0Z"


def session(
    *, at: datetime, position_s: float, paused: bool = False, item: str = "MOVIE-1",
    item_type: str = "Movie", runtime_s: int = 6000, user: str = "EMBY-1",
    session: str = "S-1", silent_since: datetime | None = None, client: str = "Web",
) -> dict:
    return {
        "Id": session,
        "UserId": user,
        "UserName": "viewer",
        "Client": client,
        "DeviceName": "PC",
        "LastActivityDate": _emby_date(silent_since or at),
        "NowPlayingItem": {
            "Id": item, "Name": "Sample title", "Type": item_type, "RunTimeTicks": runtime_s * TICK,
        },
        "PlayState": {"IsPaused": paused, "PositionTicks": int(position_s * TICK)},
    }


def saved(position_s: float, *, played: bool = False, user: str = "EMBY-1", item: str = "MOVIE-1") -> dict:
    """What Emby answers for the resume position of one title."""
    return {(user, item): StoredPosition(int(position_s * TICK), played)}


async def poll(db, at: datetime, *sessions: dict, stored: dict | None = None, grant: AsyncMock | None = None) -> None:
    source = {"source": "emby", "url": "http://emby.test", "api_key": "k"}
    with patch("services.stats_collector.collect.get_active_media_source", new=AsyncMock(return_value=source)), \
         patch("services.stats_collector.collect.get_raw_sessions", new=AsyncMock(return_value=list(sessions))), \
         patch("services.stats_collector.collect.fetch_stored_positions", new=AsyncMock(return_value=stored or {})), \
         patch("services.stats_collector.collect._session_library_name", new=AsyncMock(return_value="Films")), \
         patch("services.stats_collector.collect._grant_post_session_xp", new=grant or AsyncMock()):
        await collect_active_sessions(db, now=at)


async def rows(db) -> list[PlaybackSession]:
    query = select(PlaybackSession).order_by(PlaybackSession.id).execution_options(populate_existing=True)
    return (await db.execute(query)).scalars().all()


async def completions(db) -> list[PlaybackCompletion]:
    return (await db.execute(select(PlaybackCompletion))).scalars().all()


async def play(db, start: datetime, positions: list[float], step: timedelta, **kw) -> datetime:
    """One poll per position, ``step`` apart; returns the time of the last poll."""
    at = start
    for i, position in enumerate(positions):
        at = start + step * i
        await poll(db, at, session(at=at, position_s=position, **kw))
    return at
