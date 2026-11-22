"""A watched title keeps the time its user watched it alone, fixed at that moment."""
from datetime import timedelta

import pytest

from tests._watch_measurement_helpers import T0, completions, emby_session, play, poll, rows

pytestmark = pytest.mark.asyncio


async def test_two_titles_played_at_once_split_the_time_watched_alone(db_session):
    runtime = 600
    for i in range(1, runtime // 5 + 1):
        at = T0 + timedelta(seconds=5 * i)
        await poll(
            db_session, at,
            emby_session(at=at, position_s=5 * i, item="MOVIE-1", session="S-1", runtime_s=runtime),
            emby_session(at=at, position_s=5 * i, item="MOVIE-2", session="S-2", runtime_s=runtime),
        )

    first, second = sorted(await completions(db_session), key=lambda done: done.item_id)
    # Both count as watched, on the time of their own rows; only one was watched alone.
    assert first.watched_seconds == second.watched_seconds >= runtime * 0.75
    assert (first.exclusive_seconds, second.exclusive_seconds) == (first.watched_seconds, 0)
    # The share is fixed when the title counts as watched: the end credits add to the row only.
    assert [row.exclusive_seconds for row in await rows(db_session)] == [runtime, 0]


async def test_sittings_add_up_their_time_watched_alone(db_session):
    await play(db_session, T0, [5 + 60 * i for i in range(6)], timedelta(minutes=1), runtime_s=600)
    await poll(db_session, T0 + timedelta(minutes=6))
    next_day = T0 + timedelta(days=1)
    await play(db_session, next_day, [300 + 60 * i for i in range(5)], timedelta(minutes=1), runtime_s=600)

    (done,) = await completions(db_session)
    assert done.exclusive_seconds == done.watched_seconds == 305 + 240
