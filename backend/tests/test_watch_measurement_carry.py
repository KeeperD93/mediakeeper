"""A position that moves by jerks is counted in full, and never for more than the time spent."""
import random
from datetime import timedelta

import pytest

from services.stats_collector._measure import exclusive_shares, measure_progress
from tests._watch_measurement_helpers import STEP, T0, TICK, play, poll, rows, session


@pytest.mark.asyncio
async def test_a_jerky_position_is_counted_in_full(db_session):
    # Steps of 3 and 7 s for polls 5 s apart: the excess of one poll makes up for the next.
    positions = [100.0]
    for i in range(40):
        positions.append(positions[-1] + (3 if i % 2 else 7))
    await play(db_session, T0, positions, STEP)
    (row,) = await rows(db_session)
    assert row.watched_seconds == 200


@pytest.mark.asyncio
async def test_fractions_of_seconds_are_not_lost(db_session):
    await play(db_session, T0, [100 + 4.6 * i for i in range(101)], STEP)
    (row,) = await rows(db_session)
    assert row.watched_seconds == 460


@pytest.mark.asyncio
async def test_a_seek_forward_still_counts_only_the_time_spent(db_session):
    await play(db_session, T0, [100, 105, 2000, 2005], STEP)
    (row,) = await rows(db_session)
    assert row.watched_seconds == 15


@pytest.mark.asyncio
async def test_a_stuck_player_is_not_credited_for_its_oscillation(db_session):
    # Each report takes it back to 258 s, Emby lifts it to 262 s in between.
    await play(db_session, T0, [258 + (4 if i % 2 else 0) for i in range(60)], STEP)
    (row,) = await rows(db_session)
    assert row.watched_seconds <= 4


@pytest.mark.asyncio
async def test_a_pause_leaves_nothing_to_make_up(db_session):
    await play(db_session, T0, [100, 103], STEP)  # 2 s not credited yet
    paused_at = T0 + STEP * 2
    await poll(db_session, paused_at, session(at=paused_at, position_s=103, paused=True))
    resumed = paused_at + STEP
    await poll(db_session, resumed, session(at=resumed, position_s=108))
    (row,) = await rows(db_session)
    assert row.watched_seconds == 8


def test_the_credit_never_exceeds_the_time_spent():
    rng = random.Random(7)
    for _ in range(500):
        now, at, reference, position = T0, T0, 1000 * TICK, 1000 * TICK
        wall, credited = 0.0, 0
        for _ in range(rng.randint(5, 80)):
            elapsed = rng.choice([5, 5, 5, 6, 7, 30, 90, 2])
            step = rng.choice([0, 0.4, 3, 4, 5, 6, 7, 8, 30, 400, -2, -9, -12, -700])
            now += timedelta(seconds=elapsed)
            position = max(0, position + int(step * TICK))
            wall += elapsed
            credit, at, reference = measure_progress(reference, at, position, now, paused=rng.random() < 0.08)
            assert credit >= 0 and at <= now
            credited += credit
        assert credited <= wall


def test_unknown_reference_credits_nothing():
    assert measure_progress(None, None, 50 * TICK, T0, paused=False) == (0, T0, 50 * TICK)


def test_a_carried_jerk_is_no_extra_time_for_a_user_on_two_devices():
    assert exclusive_shares([("a", "u1", 7), ("b", "u1", 5)]) == {"a": 5}


def test_a_carried_jerk_stays_on_a_single_device():
    assert exclusive_shares([("a", "u1", 7)]) == {"a": 7}


@pytest.mark.asyncio
async def test_two_devices_with_jerky_positions_count_the_time_once(db_session):
    for i in range(61):
        at = T0 + STEP * i
        await poll(
            db_session, at,
            session(at=at, position_s=100 + 10 * (i // 2) + 3 * (i % 2)),
            session(at=at, position_s=500 + 10 * ((i + 1) // 2) - 3 * ((i + 1) % 2), item="EP-1", item_type="Episode", session="S-2"),
        )
    assert sum(row.exclusive_seconds for row in await rows(db_session)) == 300
