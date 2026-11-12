"""Simulation of the watch XP recalculation: what changes, the months it moves, the print
of the plan, and nothing written."""
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from models.portal.xp_boost import XpBoostEvent
from models.portal.xp_ledger import XpLedger
from services.portal.watch_xp_recalc import (
    build_context,
    fingerprint,
    plan_all,
    simulate_watch_xp_recalc,
)
from services.settings import set_setting
from services.stats_collector.collect import pay_watch_xp
from tests._watch_xp_helpers import T, account, watched
from tests._watch_xp_recalc_helpers import give, sitting

pytestmark = pytest.mark.asyncio
HOUR = timedelta(hours=1)


async def _snapshot(db) -> tuple[list, list]:
    ledger = (await db.execute(
        select(XpLedger.id, XpLedger.user_id, XpLedger.action, XpLedger.reference, XpLedger.xp).order_by(XpLedger.id)
    )).all()
    profiles = (await db.execute(
        select(UserProfile.user_id, UserProfile.xp, UserProfile.level).order_by(UserProfile.user_id)
    )).all()
    return ledger, profiles


async def test_a_simulation_sums_up_the_plan_and_writes_nothing(db_session):
    db = db_session
    db.add_all([
        XpBoostEvent(name="Test Event", multiplier=1.5, starts_at=T, ends_at=T + 2 * HOUR),
        XpBoostEvent(
            name="Test Event Off", multiplier=2.0, enabled=False, starts_at=T + HOUR / 2, ends_at=T + 2 * HOUR,
        ),
    ])
    alice, bob = await account(db, "alice"), await account(db, "bob")
    await sitting(db, "alice", "MOVIE-9", T - 3 * HOUR)
    await give(db, alice, "watch_movie", "MOVIE-9:2026-03-07", 10, T - 2 * HOUR)  # never watched to its end
    await watched(db, "alice", at=T - HOUR)  # 2 h, before the events: 40
    await watched(db, "bob", item="EP-1", item_type="Episode", runtime=2700, at=T + HOUR)  # 15 x 1.5 = 23
    before = await _snapshot(db)

    summary = await simulate_watch_xp_recalc(db)

    assert not db.in_transaction()  # rolled back
    assert await _snapshot(db) == before
    assert {key: summary[key] for key in (
        "players", "players_changed", "watch_xp_before", "watch_xp_after", "rows_deleted", "rows_inserted",
    )} == {
        "players": 2, "players_changed": 2, "watch_xp_before": 10, "watch_xp_after": 63,
        "rows_deleted": 1, "rows_inserted": 2,
    }
    assert [(e["name"], e["enabled"], e["titles"], e["bonus_xp"]) for e in summary["events"]] == [
        ("Test Event", True, 1, 8),  # 23 instead of 15
        ("Test Event Off", False, 1, 22),  # 15 x 3 = 45 instead of 23
    ]
    assert [(row["user_id"], row["name"], row["xp"], row["xp_after"]) for row in summary["rows"]] == [
        (alice, "Alice", 10, 40), (bob, "Bob", 0, 23),
    ]


async def test_the_print_holds_the_rows_due_up_to_the_moment_and_the_scope(db_session):
    db = db_session
    alice = await account(db, "alice")
    await give(db, alice, "daily_login", "2026-03-06", 2, T - 24 * HOUR)
    done = await watched(db, at=T)
    as_of = T + HOUR

    async def printed() -> str:
        ctx = await build_context(db, as_of)
        return fingerprint(ctx, await plan_all(db, ctx))

    first = await printed()
    await pay_watch_xp(db, [done])  # paid an instant after the simulation
    await watched(db, item="MOVIE-2", at=T + 2 * HOUR)  # watched after it
    assert await printed() == first

    await set_setting(db, "stats.exclusions", json.dumps([{"mode": "contains", "value": "test movie"}]))
    excluded = await printed()
    await set_setting(db, "stats.exclusions", "[]")
    assert await printed() == first
    await account(db, "bob")  # one more account in the scope
    assert len({first, excluded, await printed()}) == 3


async def test_the_months_whose_leader_changes_and_the_competitor_tiers(db_session):
    db = db_session
    db.add(Achievement(
        id="competitor_4", category="ranking", name_key="k", description_key="d", icon="Trophy",
        condition_type="leaderboard_first", threshold=1,
    ))
    alice, _bob, carol = [await account(db, name) for name in ("alice", "bob", "carol")]
    db.add(UserAchievement(user_id=alice, achievement_id="competitor_4", unlocked=True, progress=1))
    # March: Alice leads on a film she never finished, paid by the former rule.
    await sitting(db, "alice", "MOVIE-9", T - 3 * HOUR)
    await give(db, alice, "watch_movie", "MOVIE-9:2026-03-07", 10, T - 2 * HOUR)
    await pay_watch_xp(db, [await watched(db, "bob", item="EP-1", item_type="Episode", runtime=1320, at=T)])
    await give(db, carol, "daily_login", "2026-03-07", 5, T)

    summary = await simulate_watch_xp_recalc(db)

    assert summary["leaders_changed"] == ["2026-03"]
    assert summary["competitor_new"] == {"competitor_4": 1}  # Bob, at the next check
    assert summary["competitor_unjustified"] == {"competitor_4": 1}  # Alice keeps hers
    assert isinstance(datetime.fromisoformat(summary["as_of"]), datetime)
