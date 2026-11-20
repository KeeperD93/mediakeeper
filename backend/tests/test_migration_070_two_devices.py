"""Migration 070: another sitting of the same title still playing after the title
counted (a second device on the same account) never makes the backfill pay more."""
from datetime import timedelta

from tests._migration_070_helpers import (
    PAID,
    RUNTIME,
    admin_deletes,
    backfilled,
    done_of,
    live_values,
    watch,
)
from tests._watch_measurement_helpers import STEP, T0, emby_session, poll


async def _timeline(db, start, tracks: list) -> None:
    """``tracks``: ``(item, session, device, {poll index: (position, paused)})``, in Emby's list order."""
    last = max(k for *_, plan in tracks for k in plan)
    for k in range(last + 1):
        at = start + STEP * k
        await poll(db, at, *[
            emby_session(
                at=at, position_s=plan[k][0], paused=plan[k][1], item=item, session=session, device=device,
                runtime_s=RUNTIME,
            )
            for item, session, device, plan in tracks if k in plan
        ])
    await poll(db, start + STEP * (last + 1))  # every player gone: the rows close


def _plays(first_poll: int, first_position: int, last_position: int) -> dict:
    """5 s a poll from ``first_position`` to ``last_position``, from poll ``first_poll``."""
    return {first_poll + i: (p, False) for i, p in enumerate(range(first_position, last_position + 1, 5))}


def _tv_paused_on_the_credits() -> dict:
    """MOVIE-X to 85 % (510 s) at poll 101, then paused there for 500 s."""
    return _plays(0, 5, 510) | {102 + i: (510, True) for i in range(100)}


async def test_a_second_device_playing_on_keeps_a_refused_title_refused(db_session):
    db = db_session
    # The TV's first 120 s go to MOVIE-Z, listed first; the tablet starts a poll
    # before the TV's 85 %, then plays alone 460 s while the TV stays paused.
    await _timeline(db, T0, [
        ("MOVIE-Z", "S-Z", "DEV-Z", _plays(0, 5, 120)),
        ("MOVIE-X", "S-TV", "DEV-TV", _tv_paused_on_the_credits()),
        ("MOVIE-X", "S-TAB", "DEV-TAB", _plays(100, 5, 470)),
    ])
    live = await live_values(db)
    done = await done_of(db, "S-TV")
    assert set(live) == {done}  # the tablet never reached 85 %
    assert live[done] < PAID

    assert await backfilled(db) == live


async def test_a_sitting_first_seen_after_the_title_counted_adds_nothing(db_session):
    db = db_session
    # As above, but the tablet is first seen a poll after the TV's 85 %: its start
    # credit dates it before the completion, yet the collector never added it.
    await _timeline(db, T0, [
        ("MOVIE-Z", "S-Z", "DEV-Z", _plays(0, 5, 120)),
        ("MOVIE-X", "S-TV", "DEV-TV", _tv_paused_on_the_credits()),
        ("MOVIE-X", "S-TAB", "DEV-TAB", _plays(102, 10, 470)),
    ])
    live = await live_values(db)
    done = await done_of(db, "S-TV")
    assert set(live) == {done}
    assert live[done] < PAID

    assert await backfilled(db) == live


async def test_two_devices_paid_live_stay_paid(db_session):
    db = db_session
    await _timeline(db, T0, [
        ("MOVIE-X", "S-TV", "DEV-TV", _tv_paused_on_the_credits()),
        ("MOVIE-X", "S-TAB", "DEV-TAB", _plays(100, 5, 310)),
    ])
    live = await live_values(db)
    done = await done_of(db, "S-TV")
    assert live[done] >= PAID

    assert await backfilled(db) == live


async def test_a_deleted_sitting_hidden_by_a_second_device_is_not_paid(db_session):
    db = db_session
    # Day 0: MOVIE-X next to MOVIE-Y for 120 s (MOVIE-Y gets the time), left there.
    await watch(db, T0, 1, 24, ("MOVIE-Y", "S-Y", 24), ("MOVIE-X", "S-Xa", 24))
    # Day 1: the TV goes on alone to 85 % and stops; the tablet starts a poll
    # before, then plays alone 300 s.
    await _timeline(db, T0 + timedelta(days=1), [
        ("MOVIE-X", "S-Xb", "DEV-TV", _plays(0, 120, 510)),
        ("MOVIE-X", "S-TAB", "DEV-TAB", _plays(77, 5, 310)),
    ])
    live = await live_values(db)
    done = await done_of(db, "S-Xb")
    assert live[done] < PAID
    assert await backfilled(db) == live  # exact while every sitting is there
    await admin_deletes(db, "S-Xa")

    assert (await backfilled(db))[done] <= live[done]
