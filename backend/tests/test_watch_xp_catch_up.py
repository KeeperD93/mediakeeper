"""A watched title whose watch XP was missed is paid later, once, and never on top of a former payment."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.portal.xp_ledger import XpLedger
from services.background_tasks import BackgroundTaskManager
from services.stats_collector import WATCH_XP_CATCH_UP_SECONDS, catch_up_watch_xp
from tests._watch_xp_helpers import account, watch_rows, watched

NOW = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_a_watched_title_left_unpaid_is_paid_once(db_session):
    await account(db_session)
    done = await watched(db_session, at=NOW - timedelta(hours=1))

    assert await catch_up_watch_xp(db_session, NOW) == 1
    assert await catch_up_watch_xp(db_session, NOW) == 0

    assert await watch_rows(db_session) == [("watch_movie", f"MOVIE-1:c{done}", 40)]


@pytest.mark.asyncio
async def test_a_title_paid_when_its_playback_closed_is_not_paid_again(db_session):
    alice = await account(db_session)
    await watched(db_session, at=NOW - timedelta(hours=3))
    # The former rule paid at the closing of the playback, after the title was watched.
    db_session.add(XpLedger(
        user_id=alice, action="watch_movie", reference="MOVIE-1:2026-03-10", xp=10,
        created_at=NOW - timedelta(hours=2),
    ))
    await db_session.commit()

    assert await catch_up_watch_xp(db_session, NOW) == 0

    assert await watch_rows(db_session) == [("watch_movie", "MOVIE-1:2026-03-10", 10)]


@pytest.mark.asyncio
async def test_only_the_last_48_hours_are_caught_up(db_session):
    await account(db_session)
    await watched(db_session, at=NOW - timedelta(hours=49))

    assert await catch_up_watch_xp(db_session, NOW) == 0

    assert (await db_session.execute(select(XpLedger.id))).all() == []


@pytest.mark.asyncio
async def test_the_collector_catches_up_at_start_then_every_ten_minutes():
    clock = iter([0.0, 0.0, 5.0, WATCH_XP_CATCH_UP_SECONDS + 1.0, WATCH_XP_CATCH_UP_SECONDS + 1.0])
    polls = 0

    async def _sleep(_seconds):
        nonlocal polls
        polls += 1
        if polls > 3:  # the first sleep comes before the loop
            raise asyncio.CancelledError

    @asynccontextmanager
    async def _session(*_args, **_kwargs):
        yield None

    collect, catch_up = AsyncMock(), AsyncMock()
    with patch("services.background_tasks.asyncio.sleep", new=_sleep), \
            patch("services.background_tasks.AsyncSession", new=_session), \
            patch("services.background_tasks.time", new=SimpleNamespace(monotonic=lambda: next(clock))), \
            patch("services.background_tasks.collect_active_sessions", new=collect), \
            patch("services.background_tasks.catch_up_watch_xp", new=catch_up),             pytest.raises(asyncio.CancelledError):
        await BackgroundTaskManager(engine=AsyncMock())._periodic_stats_collection()

    assert collect.await_count == 3
    assert catch_up.await_count == 2  # at the first poll, then once ten minutes have passed
