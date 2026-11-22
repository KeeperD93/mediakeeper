"""Watch XP through the real collector: only a title counted as watched, and watched alone, pays."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.stats_collector._measure import as_utc
from tests._watch_measurement_helpers import STEP, T0, TICK, completions, emby_session, poll, rows

pytestmark = pytest.mark.asyncio
FILM = 7200


@pytest.fixture(autouse=True)
def _no_trophy_pass():
    with patch("services.portal.achievements.check_all_achievements", new=AsyncMock(return_value=[])):
        yield


async def _player(db) -> None:
    """The account of the Emby user ``EMBY-1`` (``viewer``) the polls show."""
    user = User(username="viewer", hashed_password="x", is_active=True, must_change_password=False)
    db.add(user)
    await db.flush()
    db.add(UserProfile(user_id=user.id, display_name="Viewer", role="viewer", emby_user_id="EMBY-1"))
    await db.commit()


async def _playing(db, *, started: datetime, position_s: int) -> None:
    """A row still open, last seen playing 20 seconds ago."""
    now = datetime.now(UTC)
    db.add(PlaybackSession(
        session_key="EMBY-1_MOVIE-1_S-1:1", emby_session_key="EMBY-1_MOVIE-1_S-1", user_id="EMBY-1",
        user_name="viewer", item_id="MOVIE-1", item_name="Test Movie", item_type="Movie",
        duration_ticks=FILM * TICK, position_ticks=position_s * TICK, started_at=started,
        last_seen_at=now - timedelta(seconds=20), is_active=True,
    ))
    await db.commit()


async def _watch_rows(db) -> list[tuple[str, str, int]]:
    found = await db.execute(select(XpLedger.action, XpLedger.reference, XpLedger.xp).order_by(XpLedger.id))
    return [tuple(row) for row in found.all()]


async def test_a_film_left_on_pause_earns_nothing(db_session):
    await _player(db_session)
    # Two hours of film, stopped at 30 % after a three-day pause.
    await _playing(db_session, started=datetime.now(UTC) - timedelta(days=3), position_s=2160)

    await poll(db_session, datetime.now(UTC), real_xp=True)  # the player is gone: the row closes

    assert (await rows(db_session))[0].is_active is False
    assert await _watch_rows(db_session) == []


async def test_a_seek_to_the_end_earns_nothing(db_session):
    await _player(db_session)
    # Two minutes of film, then a jump to 97 %.
    await _playing(db_session, started=datetime.now(UTC) - timedelta(minutes=2), position_s=6984)

    await poll(db_session, datetime.now(UTC), real_xp=True)

    assert (await rows(db_session))[0].is_active is False
    assert await _watch_rows(db_session) == []


async def _two_films_at_once(db, runtime: int) -> datetime:
    at = T0
    for i in range(1, runtime // 5 + 1):
        at = T0 + STEP * i
        await poll(
            db, at,
            emby_session(at=at, position_s=5 * i, item="MOVIE-1", session="S-1", runtime_s=runtime),
            emby_session(at=at, position_s=5 * i, item="MOVIE-2", session="S-2", runtime_s=runtime),
            real_xp=True,
        )
    return at


async def test_two_films_played_at_once_pay_only_the_one_watched_alone(db_session):
    await _player(db_session)
    last = await _two_films_at_once(db_session, 600)
    await poll(db_session, last + STEP, real_xp=True)  # both players closed

    first = next(done for done in await completions(db_session) if done.item_id == "MOVIE-1")
    # 10 minutes of film: 20 XP an hour gives 3 XP.
    assert await _watch_rows(db_session) == [("watch_movie", f"MOVIE-1:c{first.id}", 3)]


async def test_a_title_watched_over_two_sittings_pays_once_when_it_counts(db_session):
    await _player(db_session)
    for i in range(6):  # first evening: the first half, then the player is closed
        at = T0 + timedelta(minutes=i)
        await poll(db_session, at, emby_session(at=at, position_s=5 + 60 * i, runtime_s=600), real_xp=True)
    await poll(db_session, T0 + timedelta(minutes=6), real_xp=True)
    assert await _watch_rows(db_session) == []
    next_day = T0 + timedelta(days=1)
    for i in range(5):
        at = next_day + timedelta(minutes=i)
        await poll(db_session, at, emby_session(at=at, position_s=300 + 60 * i, runtime_s=600), real_xp=True)

    (done,) = await completions(db_session)
    assert await _watch_rows(db_session) == [("watch_movie", f"MOVIE-1:c{done.id}", 3)]
    paid_at = await db_session.scalar(select(XpLedger.created_at))
    assert as_utc(paid_at) == as_utc(done.completed_at)


async def test_the_collector_hands_over_plain_ids_after_its_commit(db_session):
    pay, closed = AsyncMock(return_value=0), AsyncMock()
    with patch("services.stats_collector.collect.pay_watch_xp", new=pay), \
            patch("services.stats_collector.collect._after_rows_closed", new=closed):
        at = T0
        for i in range(11):
            at = T0 + timedelta(minutes=i)
            await poll(db_session, at, emby_session(at=at, position_s=5 + 60 * i, runtime_s=600), real_xp=True)
        await poll(db_session, at + STEP, real_xp=True)

    (done,), (row,) = await completions(db_session), await rows(db_session)
    pay.assert_awaited_once()
    assert pay.await_args.args[1] == [done.id]
    closed.assert_awaited_once()
    assert closed.await_args.args[1] == [row.id]
