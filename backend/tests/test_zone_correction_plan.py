"""What the correction would take back: the trophies the UTC clock gave, and only those."""
from datetime import datetime

import pytest

from models.portal.audit import AdminAuditLog
from models.portal.xp_ledger import XpLedger
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal.achievement_defs import ACHIEVEMENT_DEFS
from services.portal.achievements import seed_achievements
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ACHIEVEMENT_LOCKED,
    ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
    ACTION_SYSTEM_TIMEZONE_CHANGED,
)
from services.portal.zone_correction import ZoneCorrectionRefused, simulate_zone_correction
from services.settings import set_setting
from tests._zone_correction_helpers import (
    DAWN_IN_PARIS,
    DAWN_UTC_ONLY,
    ZONE_SAVED_AT,
    at,
    hold,
    play,
    player,
    profile_of,
    save_zone,
    unlocked,
)

EARLY = "secret_early_bird"


def _removed(summary: dict) -> dict[str, tuple[int, int]]:
    return {r["achievement_id"]: (r["direct"], r["cascade"]) for r in summary["removals"]}


def _kept(entries: list[dict]) -> dict[str, int]:
    return {entry["achievement_id"]: entry["count"] for entry in entries}


async def _alice_with_dawn(db, when=DAWN_UTC_ONLY, **hold_kwargs) -> int:
    await seed_achievements(db)
    await save_zone(db)
    alice = await player(db, "alice")
    play(db, "alice", when)
    await hold(db, alice, EARLY, **hold_kwargs)
    return alice


@pytest.mark.asyncio
async def test_refused_while_no_zone_is_saved(db_session):
    await seed_achievements(db_session)
    with pytest.raises(ZoneCorrectionRefused) as refused:
        await simulate_zone_correction(db_session)
    assert refused.value.code == "zone_not_chosen"


@pytest.mark.asyncio
async def test_refused_when_the_first_save_left_no_trace(db_session):
    await seed_achievements(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    with pytest.raises(ZoneCorrectionRefused) as refused:
        await simulate_zone_correction(db_session)
    assert refused.value.code == "zone_saved_at_unknown"


@pytest.mark.asyncio
async def test_refused_when_only_a_later_change_left_a_trace(db_session):
    # The zone came back with a restore, then changed: when UTC ended is unknown.
    await seed_achievements(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris", commit=False)
    db_session.add(AdminAuditLog(
        action=ACTION_SYSTEM_TIMEZONE_CHANGED, created_at=ZONE_SAVED_AT,
        payload={"from": "Europe/Berlin", "to": "Europe/Paris"},
    ))
    await db_session.commit()
    with pytest.raises(ZoneCorrectionRefused) as refused:
        await simulate_zone_correction(db_session)
    assert refused.value.code == "zone_saved_at_unknown"


@pytest.mark.asyncio
async def test_a_trophy_earned_in_utc_only_is_taken_back(db_session):
    await _alice_with_dawn(db_session)
    summary = await simulate_zone_correction(db_session)
    assert _removed(summary) == {EARLY: (1, 0)}
    assert summary["timezone"] == "Europe/Paris"
    assert summary["zone_saved_at"] == ZONE_SAVED_AT.isoformat()
    assert (summary["players_affected"], summary["xp_removed"], summary["removed_imported"]) == (1, 40, 0)


@pytest.mark.asyncio
async def test_a_trophy_earned_in_the_zone_stays(db_session):
    await _alice_with_dawn(db_session, when=DAWN_IN_PARIS)
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == [] and summary["kept_nowhere"] == []


@pytest.mark.asyncio
async def test_a_trophy_unlocked_after_the_zone_was_saved_stays(db_session):
    # Unlocked on the zone's clock: if its rule fails now, something else than the hour moved.
    await _alice_with_dawn(db_session, unlocked_at=at(2026, 2, 3))
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == []


@pytest.mark.asyncio
async def test_a_trophy_met_on_neither_clock_stays_and_is_counted(db_session):
    await seed_achievements(db_session)
    await save_zone(db_session)
    alice = await player(db_session, "alice")
    await hold(db_session, alice, EARLY)
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == []
    assert _kept(summary["kept_nowhere"]) == {EARLY: 1}


@pytest.mark.asyncio
async def test_a_trophy_handed_out_by_an_admin_stays_and_is_counted(db_session):
    alice = await _alice_with_dawn(db_session)
    db_session.add(AdminAuditLog(
        action=ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, target_user_id=alice, payload={"achievement_id": EARLY},
    ))
    await db_session.commit()
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == []
    assert _kept(summary["kept_gifts"]) == {EARLY: 1}


@pytest.mark.asyncio
async def test_a_gift_taken_back_by_the_admin_and_earned_again_is_judged(db_session):
    alice = await _alice_with_dawn(db_session)
    for action in (ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, ACTION_DEBUG_ACHIEVEMENT_LOCKED):
        db_session.add(AdminAuditLog(action=action, target_user_id=alice, payload={"achievement_id": EARLY}))
    await db_session.commit()
    summary = await simulate_zone_correction(db_session)
    assert _removed(summary) == {EARLY: (1, 0)}


@pytest.mark.asyncio
async def test_a_removal_resting_on_imported_history_is_counted_apart(db_session):
    await seed_achievements(db_session)
    await save_zone(db_session)
    alice = await player(db_session, "alice")
    play(db_session, "alice", DAWN_UTC_ONLY, key="js_12345")
    await hold(db_session, alice, EARLY)
    summary = await simulate_zone_correction(db_session)
    assert summary["removed_imported"] == 1
    assert summary["removals"][0]["imported"] == 1


@pytest.mark.asyncio
async def test_collector_goes_with_the_trophy_it_counted(db_session):
    alice = await _alice_with_dawn(db_session)
    movies = [d["id"] for d in ACHIEVEMENT_DEFS if d["condition_type"] == "watch_movies"][:4]
    for achievement_id in [*movies, "collector_1"]:
        await hold(db_session, alice, achievement_id, xp=0)
    summary = await simulate_zone_correction(db_session)
    assert _removed(summary) == {EARLY: (1, 0), "collector_1": (0, 1)}


@pytest.mark.asyncio
async def test_a_renamed_player_is_judged_on_all_their_emby_names(db_session):
    # The play carries an older Emby name: the end of that playback passed it to the check.
    await seed_achievements(db_session)
    await save_zone(db_session)
    alice = await player(db_session, "alice")
    play(db_session, "alice", DAWN_UTC_ONLY, user_name="Alice Old")
    await hold(db_session, alice, EARLY)
    summary = await simulate_zone_correction(db_session)
    assert _removed(summary) == {EARLY: (1, 0)}


@pytest.mark.asyncio
async def test_a_deactivated_player_is_corrected_too(db_session):
    await seed_achievements(db_session)
    await save_zone(db_session)
    bob = await player(db_session, "bob", active=False)
    play(db_session, "bob", DAWN_UTC_ONLY)
    await hold(db_session, bob, EARLY)
    summary = await simulate_zone_correction(db_session)
    assert _removed(summary) == {EARLY: (1, 0)}


async def _activity(db, *rows: tuple[int, datetime]) -> None:
    for user_id, created_at in rows:
        db.add(XpLedger(
            user_id=user_id, action="watch_movie", reference=f"item:{created_at.isoformat()}",
            xp=10, created_at=created_at,
        ))
    await db.commit()


async def _alice_and_bob_in_new_york(db) -> tuple[int, int]:
    await seed_achievements(db)
    await save_zone(db, "America/New_York")
    return await player(db, "alice"), await player(db, "bob")


@pytest.mark.asyncio
async def test_competitor_is_taken_back_when_the_zone_splits_its_month(db_session):
    # 1 March 03:00 UTC is still February in New York: March loses its second player.
    alice, bob = await _alice_and_bob_in_new_york(db_session)
    await _activity(db_session, (alice, at(2026, 3, 5)), (bob, at(2026, 3, 1, 3)))
    await hold(db_session, alice, "competitor_1")
    summary = await simulate_zone_correction(db_session)
    assert _removed(summary) == {"competitor_1": (1, 0)}
    assert summary["competitor_months"] == {"changed": 1, "created": 0}


@pytest.mark.asyncio
async def test_a_month_only_the_zone_has_is_counted(db_session):
    alice, bob = await _alice_and_bob_in_new_york(db_session)
    await _activity(db_session, (alice, at(2026, 3, 1, 2)), (bob, at(2026, 3, 1, 3)))
    await hold(db_session, alice, "competitor_1")
    summary = await simulate_zone_correction(db_session)
    assert summary["removals"] == []
    assert summary["competitor_months"] == {"changed": 2, "created": 1}


@pytest.mark.asyncio
async def test_the_simulation_writes_nothing(db_session):
    alice = await _alice_with_dawn(db_session)
    first = await simulate_zone_correction(db_session)
    second = await simulate_zone_correction(db_session)
    assert first == second and _removed(second) == {EARLY: (1, 0)}
    assert await unlocked(db_session, alice) == {EARLY}
    assert (await profile_of(db_session, alice)).xp == 40
