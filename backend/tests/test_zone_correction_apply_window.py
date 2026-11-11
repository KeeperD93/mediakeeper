"""An apply when players change between the plan the admin confirmed and the writing."""
import logging
from pathlib import Path

import pytest
from sqlalchemy import select

from models.portal.audit import AdminAuditLog
from models.portal.xp_ledger import XpLedger
from services.backup.create import BackupResult
from services.portal import admin_debug
from services.portal.achievement_defs import ACHIEVEMENT_DEFS
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ACHIEVEMENT_LOCKED,
    ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
    ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
    ACTION_DEBUG_ZONE_CORRECTION,
    ACTION_DEBUG_ZONE_CORRECTION_PLAYER,
)
from services.portal.zone_correction import _run
from services.portal.zone_correction._context import build_context, load_admin_gifts
from tests._zone_correction_helpers import (
    APPLY,
    ARCHIVE,
    DAWN_IN_PARIS,
    DAWN_UTC_ONLY,
    EARLY,
    SIMULATE,
    alice_with_early_bird,
    confirmation,
    freeze,
    hold,
    play,
    player,
    profile_of,
    unlocked,
)

COLLECTOR = "collector_1"
MOVIES = [d["id"] for d in ACHIEVEMENT_DEFS if d["condition_type"] == "watch_movies"]


@pytest.fixture(autouse=True)
def _mid_month(monkeypatch):
    freeze(monkeypatch)


def _while_backing_up(monkeypatch, change) -> None:
    """Runs ``change`` between the plan the admin confirmed and the writing."""
    async def backup(db, label=""):
        await change(db)
        return BackupResult(Path(ARCHIVE), ())

    monkeypatch.setattr(_run, "create_backup", backup)


async def _hold_all(db, user_id: int, *achievement_ids: str) -> None:
    for achievement_id in achievement_ids:
        await hold(db, user_id, achievement_id, xp=0)


async def _dawn_player(db, name: str) -> int:
    """Another player holding the early bird of a dawn that is one in UTC only."""
    user_id = await player(db, name, xp=10)
    play(db, name, DAWN_UTC_ONLY)
    await hold(db, user_id, EARLY)
    return user_id


async def _player_audits(db) -> list[AdminAuditLog]:
    db.expire_all()
    return (await db.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == ACTION_DEBUG_ZONE_CORRECTION_PLAYER)
    )).scalars().all()


@pytest.mark.asyncio
async def test_a_player_who_would_lose_a_trophy_not_shown_is_left_whole(client, db_session, monkeypatch, caplog):
    alice = await alice_with_early_bird(client, db_session)
    await _hold_all(db_session, alice, *MOVIES[:4])
    bob = await _dawn_player(db_session, "bob")
    confirmed = await confirmation(client)

    # Five trophies once the early bird is counted: Collector rests on it, and was not in the plan.
    _while_backing_up(monkeypatch, lambda db: _hold_all(db, alice, COLLECTOR))
    with caplog.at_level(logging.WARNING, logger=_run.logger.name):
        resp = await client.post(APPLY, json=confirmed)

    assert resp.json()["applied"] == {"players": 1, "removed": 1, "xp_removed": 40, "failed": 0, "changed": 1}
    assert f"player {alice} changed" in caplog.text
    assert await unlocked(db_session, alice) == {EARLY, COLLECTOR, *MOVIES[:4]}
    assert (await profile_of(db_session, alice)).xp == 110
    assert (await db_session.execute(select(XpLedger).where(XpLedger.user_id == alice))).first()
    assert await unlocked(db_session, bob) == set()
    assert [row.target_user_id for row in await _player_audits(db_session)] == [bob]
    run = (await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == ACTION_DEBUG_ZONE_CORRECTION)
    )).scalar_one()
    assert run.payload["changed"] == 1


@pytest.mark.asyncio
async def test_a_trophy_shown_for_another_player_does_not_cover_this_one(client, db_session, monkeypatch):
    alice = await alice_with_early_bird(client, db_session)
    await _hold_all(db_session, alice, *MOVIES[:4])
    bob = await _dawn_player(db_session, "bob")
    await _hold_all(db_session, bob, *MOVIES[:4], COLLECTOR)
    simulated = (await client.get(SIMULATE)).json()
    assert simulated["removed_total"] == 3  # the early bird twice, Collector for Bob alone

    _while_backing_up(monkeypatch, lambda db: _hold_all(db, alice, COLLECTOR))
    resp = await client.post(APPLY, json={"timezone": simulated["timezone"], "plan": simulated["plan"]})

    assert resp.json()["applied"] == {"players": 1, "removed": 2, "xp_removed": 40, "failed": 0, "changed": 1}
    assert await unlocked(db_session, alice) == {EARLY, COLLECTOR, *MOVIES[:4]}
    assert await unlocked(db_session, bob) == set(MOVIES[:4])


@pytest.mark.asyncio
async def test_a_player_left_whole_does_not_keep_the_transaction_open(client, db_session):
    alice = await alice_with_early_bird(client, db_session)
    ctx = await build_context(db_session)
    with pytest.raises(_run._PlanGrew):
        await _run._apply_player(db_session, ctx, alice, set(), {})
    assert not db_session.in_transaction()


@pytest.mark.asyncio
async def test_a_trophy_lost_by_knock_on_and_shown_is_taken(client, db_session, monkeypatch):
    alice = await alice_with_early_bird(client, db_session)
    await _hold_all(db_session, alice, *MOVIES[:4], COLLECTOR)
    confirmed = await confirmation(client)

    async def nothing_happens(db):
        return None

    _while_backing_up(monkeypatch, nothing_happens)
    resp = await client.post(APPLY, json=confirmed)

    assert resp.json()["applied"] == {"players": 1, "removed": 2, "xp_removed": 40, "failed": 0, "changed": 0}
    assert await unlocked(db_session, alice) == set(MOVIES[:4])
    undo = (await _player_audits(db_session))[0].payload["undo"]
    assert set(undo["trophies"]) == {EARLY, COLLECTOR}
    assert [row["xp"] for row in undo["ledger"]] == [40]  # Collector was held without a ledger row


@pytest.mark.asyncio
async def test_a_player_who_would_lose_less_than_shown_is_still_corrected(client, db_session, monkeypatch):
    alice = await alice_with_early_bird(client, db_session)
    await _hold_all(db_session, alice, *MOVIES[:4], COLLECTOR)
    simulated = (await client.get(SIMULATE)).json()
    assert simulated["removed_total"] == 2

    # A fifth trophy besides the early bird: Collector no longer rests on it.
    _while_backing_up(monkeypatch, lambda db: _hold_all(db, alice, MOVIES[4]))
    resp = await client.post(APPLY, json={"timezone": simulated["timezone"], "plan": simulated["plan"]})

    assert resp.json()["applied"] == {"players": 1, "removed": 1, "xp_removed": 40, "failed": 0, "changed": 0}
    assert await unlocked(db_session, alice) == {COLLECTOR, *MOVIES[:5]}


@pytest.mark.asyncio
async def test_a_player_with_nothing_left_to_take_is_not_counted_as_changed(client, db_session, monkeypatch):
    alice = await alice_with_early_bird(client, db_session)
    confirmed = await confirmation(client)

    async def dawn_in_the_zone(db):
        play(db, "alice", DAWN_IN_PARIS)
        await db.commit()

    _while_backing_up(monkeypatch, dawn_in_the_zone)
    resp = await client.post(APPLY, json=confirmed)

    assert resp.json()["applied"] == {"players": 0, "removed": 0, "xp_removed": 0, "failed": 0, "changed": 0}
    assert await unlocked(db_session, alice) == {EARLY}
    assert await _player_audits(db_session) == []


@pytest.mark.asyncio
async def test_a_trophy_given_back_by_hand_during_the_backup_is_kept(client, db_session, monkeypatch):
    alice = await alice_with_early_bird(client, db_session)
    await _hold_all(db_session, alice, *MOVIES[:4], COLLECTOR)
    confirmed = await confirmation(client)  # Collector shown: it rests on the early bird

    async def given_back_by_hand(db):
        await admin_debug.admin_lock_achievement(db, alice, COLLECTOR)
        await admin_debug.admin_unlock_achievement(db, alice, COLLECTOR)

    _while_backing_up(monkeypatch, given_back_by_hand)
    resp = await client.post(APPLY, json=confirmed)

    assert resp.json()["applied"] == {"players": 1, "removed": 1, "xp_removed": 40, "failed": 0, "changed": 0}
    assert await unlocked(db_session, alice) == {COLLECTOR, *MOVIES[:4]}


@pytest.mark.asyncio
async def test_the_gifts_of_one_player_follow_the_same_history_as_everyone_s(db_session):
    alice, bob = 1, 2
    for action, target, achievement_id in [
        (ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, alice, "early"),
        (ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, bob, "early"),
        (ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, alice, "reset"),
        (ACTION_DEBUG_ACHIEVEMENT_RESET_ALL, None, "reset"),
        (ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, alice, "taken_back"),
        (ACTION_DEBUG_ACHIEVEMENT_LOCKED, alice, "taken_back"),
    ]:
        await record_audit(
            db_session, admin_user_id=None, target_user_id=target, action=action,
            payload={"achievement_id": achievement_id}, commit=False,
        )
    await db_session.commit()

    assert await load_admin_gifts(db_session) == {(alice, "early"), (bob, "early")}
    assert await load_admin_gifts(db_session, alice) == {(alice, "early")}
