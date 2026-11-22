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
from services.stats_collector.collect import pay_watch_xp
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
@pytest.mark.parametrize(("later", "caught"), [(20, 0), (30, 1)])
async def test_a_later_viewing_paid_first_blocks_a_caught_up_title_within_24_hours_only(db_session, later, caught):
    await account(db_session)
    first = await watched(db_session, at=NOW - timedelta(hours=40))
    again = await watched(db_session, at=NOW - timedelta(hours=40 - later))
    assert await pay_watch_xp(db_session, [again]) == 1  # paid live, before the first one was caught up

    assert await catch_up_watch_xp(db_session, NOW) == caught

    assert {reference for _, reference, _ in await watch_rows(db_session)} == {
        f"MOVIE-1:c{done}" for done in ([again, first] if caught else [again])
    }


@pytest.mark.asyncio
async def test_a_former_payment_dated_long_after_the_title_still_blocks_it(db_session):
    alice = await account(db_session)
    await watched(db_session, at=NOW - timedelta(hours=40))
    # Its playback stayed open (paused) and closed 30 hours later: the former rule paid then.
    db_session.add(XpLedger(
        user_id=alice, action="watch_movie", reference="MOVIE-1:2026-03-10", xp=10,
        created_at=NOW - timedelta(hours=10),
    ))
    await db_session.commit()

    assert await catch_up_watch_xp(db_session, NOW) == 0


@pytest.mark.asyncio
async def test_only_the_last_48_hours_are_caught_up(db_session):
    await account(db_session)
    await watched(db_session, at=NOW - timedelta(hours=49))

    assert await catch_up_watch_xp(db_session, NOW) == 0

    assert (await db_session.execute(select(XpLedger.id))).all() == []


async def _run_the_collector(clock: list[float], polls: int, collect: AsyncMock, catch_up: AsyncMock) -> None:
    """``polls`` turns of the collector loop, its clock reading ``clock`` in turn."""
    ticks, slept = iter(clock), 0

    async def _sleep(_seconds):
        nonlocal slept
        slept += 1
        if slept > polls:  # the first sleep comes before the loop
            raise asyncio.CancelledError

    @asynccontextmanager
    async def _session(*_args, **_kwargs):
        yield None

    with patch("services.background_tasks.asyncio.sleep", new=_sleep), \
            patch("services.background_tasks.AsyncSession", new=_session), \
            patch("services.background_tasks.time", new=SimpleNamespace(monotonic=lambda: next(ticks))), \
            patch("services.background_tasks.collect_active_sessions", new=collect), \
            patch("services.background_tasks.catch_up_watch_xp", new=catch_up), \
            pytest.raises(asyncio.CancelledError):
        await BackgroundTaskManager(engine=AsyncMock())._periodic_stats_collection()


@pytest.mark.asyncio
async def test_the_collector_catches_up_at_start_then_every_ten_minutes():
    later = WATCH_XP_CATCH_UP_SECONDS + 1.0
    collect, catch_up = AsyncMock(), AsyncMock()

    await _run_the_collector([0.0, 0.0, 5.0, later, later], 3, collect, catch_up)

    assert collect.await_count == 3
    assert catch_up.await_count == 2  # at the first poll, then once ten minutes have passed


@pytest.mark.asyncio
async def test_a_failed_catch_up_is_logged_with_its_trace_and_the_polls_go_on(caplog):
    collect, catch_up = AsyncMock(), AsyncMock(side_effect=RuntimeError("test failure"))

    await _run_the_collector([0.0, 0.0, 5.0], 2, collect, catch_up)

    assert collect.await_count == 2
    (failure,) = [r for r in caplog.records if r.getMessage().startswith("Error catching up watch XP")]
    assert failure.exc_info is not None
