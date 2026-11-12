"""The day streaks in the correction: Regular on the days watched, Faithful on the start days."""
from datetime import timedelta

import pytest

from services.portal.achievements import seed_achievements
from services.portal.achievements_local_time import local_plays
from services.portal.zone_correction import _judge, simulate_zone_correction
from tests._zone_correction_helpers import at, freeze, hold, play, player, save_zone


@pytest.fixture(autouse=True)
def _mid_month(monkeypatch):
    freeze(monkeypatch)


async def _alice(db) -> int:
    await seed_achievements(db)
    await save_zone(db)
    return await player(db, "alice")


async def _a_launch_alone_on_the_11th_in_paris(db, *tiers: str) -> None:
    # Paris is UTC+1: two minutes started on the 11th there, the next ten after midnight.
    alice = await _alice(db)
    play(db, "alice", at(2026, 1, 10, 12), seconds=600)
    play(db, "alice", at(2026, 1, 11, 12), seconds=120)
    play(db, "alice", at(2026, 1, 11, 23, 10), seconds=600)
    play(db, "alice", at(2026, 1, 12, 12), seconds=600)
    for tier in tiers:
        await hold(db, alice, tier, xp=0)


@pytest.mark.asyncio
async def test_a_regular_tier_the_start_days_hold_in_the_zone_stays(db_session):
    await _a_launch_alone_on_the_11th_in_paris(db_session, "regular_1")
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == [] and summary["kept_nowhere"] == []


@pytest.mark.asyncio
async def test_the_old_rule_gives_the_same_outcome_for_a_launch_alone(db_session, monkeypatch):
    """Judged on the start days alone, as before the days watched, the player keeps the same."""
    await _a_launch_alone_on_the_11th_in_paris(db_session, "regular_1")
    summary = await simulate_zone_correction(db_session)
    monkeypatch.setattr(
        _judge, "watch_days", lambda rows, zone, **_: {play.at.date() for play in local_plays(rows, zone)},
    )
    assert await simulate_zone_correction(db_session) == summary


@pytest.mark.asyncio
async def test_a_regular_tier_neither_rule_holds_in_the_zone_is_taken_back(db_session):
    # The 11th in UTC is the 12th in Paris, which neither starts nor watches anything on the 11th.
    alice = await _alice(db_session)
    play(db_session, "alice", at(2026, 1, 10, 12), seconds=600)
    play(db_session, "alice", at(2026, 1, 11, 23, 30), seconds=600)
    play(db_session, "alice", at(2026, 1, 12, 12), seconds=600)
    await hold(db_session, alice, "regular_1")
    summary = await simulate_zone_correction(db_session)
    assert [(r["achievement_id"], r["direct"]) for r in summary["removals"]] == [("regular_1", 1)]


@pytest.mark.asyncio
async def test_a_regular_tier_only_the_utc_start_days_gave_is_taken_back(db_session):
    # Two minutes started on the 11th in UTC, past midnight in Paris: three start days in UTC,
    # two days watched there, and two days on either rule in Paris.
    alice = await _alice(db_session)
    play(db_session, "alice", at(2026, 1, 10, 12), seconds=600)
    play(db_session, "alice", at(2026, 1, 11, 23, 30), seconds=120)
    play(db_session, "alice", at(2026, 1, 12, 12), seconds=600)
    await hold(db_session, alice, "regular_1")
    summary = await simulate_zone_correction(db_session)
    assert [(r["achievement_id"], r["direct"]) for r in summary["removals"]] == [("regular_1", 1)]
    assert summary["kept_nowhere"] == []


@pytest.mark.asyncio
async def test_a_day_streak_counts_the_watched_hours_on_both_clocks(db_session):
    # Paris is UTC+1: the first film runs until 00:30 on the 11th there, the second starts on the 12th.
    alice = await _alice(db_session)
    play(db_session, "alice", at(2026, 1, 10, 22, 30), seconds=3600)
    play(db_session, "alice", at(2026, 1, 11, 23, 30), seconds=600)
    play(db_session, "alice", at(2026, 1, 12, 12), seconds=600)
    await hold(db_session, alice, "regular_1")
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == [] and summary["kept_nowhere"] == []


@pytest.mark.asyncio
async def test_a_half_hour_zone_keeps_a_day_watched_across_its_midnight(db_session):
    # Kolkata is UTC+5:30: 23:50 to 00:25 there puts 25 minutes on the 11th, inside the
    # 18:00 UTC hour that starts on the 10th. Hour by hour alone, the 11th would be lost.
    await seed_achievements(db_session)
    await save_zone(db_session, "Asia/Kolkata")
    alice = await player(db_session, "alice")
    play(db_session, "alice", at(2026, 1, 10, 6, 30), seconds=600)
    play(db_session, "alice", at(2026, 1, 10, 18, 20), seconds=35 * 60)
    play(db_session, "alice", at(2026, 1, 11, 20), seconds=600)
    play(db_session, "alice", at(2026, 1, 12, 6, 30), seconds=600)
    await hold(db_session, alice, "regular_1")
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == []


@pytest.mark.asyncio
async def test_faithful_is_judged_on_the_days_a_play_started_on(db_session):
    # A minute at noon every day of 2025: a run on both clocks, though never five minutes a day.
    alice = await _alice(db_session)
    for day in range(365):
        play(db_session, "alice", at(2025, 1, 1, 12) + timedelta(days=day))
    await hold(db_session, alice, "secret_dedication")
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == [] and summary["kept_nowhere"] == []


@pytest.mark.asyncio
async def test_the_days_watched_are_built_once_per_clock(db_session, monkeypatch):
    await _a_launch_alone_on_the_11th_in_paris(
        db_session, "regular_1", "regular_2", "regular_3", "regular_4", "regular_5",
    )
    zones = []
    build = _judge.watch_days
    monkeypatch.setattr(
        _judge, "watch_days", lambda rows, zone, **kw: zones.append(zone) or build(rows, zone, **kw),
    )
    await simulate_zone_correction(db_session)
    assert len(zones) == 2
