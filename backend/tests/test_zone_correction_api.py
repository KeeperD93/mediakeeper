"""The correction endpoints: admin only, the plan the admin has seen, a full backup first."""
from pathlib import Path

import pytest
from sqlalchemy import select

from models.portal.achievement import UserAchievement
from models.portal.audit import AdminAuditLog
from models.portal.xp_ledger import XpLedger
from services.backup.create import BackupResult
from services.portal import daily_digest
from services.portal.achievement_defs import ACHIEVEMENT_DEFS
from services.portal.achievements import seed_achievements
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ZONE_CORRECTION,
    ACTION_DEBUG_ZONE_CORRECTION_PLAYER,
)
from services.portal.zone_correction import _run
from services.portal.zone_correction._context import build_context
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token
from tests._zone_correction_helpers import (
    DAWN_IN_PARIS,
    DAWN_UTC_ONLY,
    freeze,
    hold,
    play,
    player,
    profile_of,
    save_zone,
    unlocked,
)

SIMULATE = "/api/portal/admin/debug/zone-correction/simulate"
APPLY = "/api/portal/admin/debug/zone-correction/apply"
EARLY = "secret_early_bird"
COLLECTOR = "collector_1"
MOVIES = [d["id"] for d in ACHIEVEMENT_DEFS if d["condition_type"] == "watch_movies"]
ARCHIVE ="mediakeeper_backup_20260201_120000_zone_correction.zip"


@pytest.fixture(autouse=True)
def _mid_month(monkeypatch):
    freeze(monkeypatch)


@pytest.fixture
def backups(monkeypatch):
    """The labels of the backups made; a part named in ``failed`` is missing from them."""
    made: list[str] = []
    failed: list[str] = []

    async def fake_backup(db, label=""):
        made.append(label)
        return BackupResult(Path(ARCHIVE), tuple(failed))

    monkeypatch.setattr(_run, "create_backup", fake_backup)
    return made, failed


async def _as(client, db, name: str, role: str) -> None:
    user, _ = await make_portal_user(db, username=name, role=role)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))


async def _alice(client, db) -> int:
    """Alice holds the early bird of a dawn that is one in UTC only; 70 XP of her own."""
    await seed_achievements(db)
    await save_zone(db)
    await _as(client, db, "admin", "admin")
    alice = await player(db, "alice", xp=70)
    play(db, "alice", DAWN_UTC_ONLY)
    await hold(db, alice, EARLY)
    return alice


async def _confirmation(client) -> dict:
    body = (await client.get(SIMULATE)).json()
    return {"timezone": body["timezone"], "plan": body["plan"]}


def _while_backing_up(monkeypatch, change) -> None:
    """Runs ``change`` between the plan the admin confirmed and the writing."""
    async def backup(db, label=""):
        await change(db)
        return BackupResult(Path(ARCHIVE), ())

    monkeypatch.setattr(_run, "create_backup", backup)


async def _hold_all(db, user_id: int, *achievement_ids: str) -> None:
    for achievement_id in achievement_ids:
        await hold(db, user_id, achievement_id, xp=0)


async def _player_audits(db) -> list[AdminAuditLog]:
    db.expire_all()
    return (await db.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == ACTION_DEBUG_ZONE_CORRECTION_PLAYER)
    )).scalars().all()


@pytest.mark.asyncio
async def test_a_viewer_reaches_neither_endpoint(client, db_session):
    await _as(client, db_session, "bob", "viewer")
    assert (await client.get(SIMULATE)).status_code == 403
    assert (await client.post(APPLY, json={"timezone": "UTC", "plan": "x"})).status_code == 403


@pytest.mark.asyncio
async def test_nothing_is_simulated_before_a_zone_is_saved(client, db_session):
    await seed_achievements(db_session)
    await _as(client, db_session, "admin", "admin")
    resp = await client.get(SIMULATE)
    assert (resp.status_code, resp.json()["detail"]) == (409, "zone_not_chosen")


@pytest.mark.asyncio
async def test_apply_takes_back_the_trophy_its_xp_and_its_badge(client, db_session, backups):
    alice = await _alice(client, db_session)
    profile = await profile_of(db_session, alice)
    profile.level, profile.selected_badges = 1, [EARLY]
    await db_session.commit()
    daily_digest._cache_set(alice, "2026-02-02", "fr", {"cached": True})
    simulated = (await client.get(SIMULATE)).json()
    assert (simulated["players_losing_level"], simulated["max_level_loss"]) == (1, 1)

    resp = await client.post(APPLY, json={"timezone": simulated["timezone"], "plan": simulated["plan"]})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["applied"] == {"players": 1, "removed": 1, "xp_removed": 40, "failed": 0, "changed": 0}
    assert (body["backup"], backups[0]) == (ARCHIVE, ["zone_correction"])

    assert await unlocked(db_session, alice) == set()
    row = (await db_session.execute(select(UserAchievement).where(
        UserAchievement.user_id == alice, UserAchievement.achievement_id == EARLY,
    ))).scalar_one()
    assert (row.unlocked, row.unlocked_at, row.progress) == (False, None, 0)
    profile = await profile_of(db_session, alice)
    assert (profile.xp, profile.level, profile.selected_badges) == (70, 0, None)
    assert (await db_session.execute(select(XpLedger).where(XpLedger.user_id == alice))).first() is None
    assert all(key[0] != alice for key in daily_digest._digest_cache)

    audits = {
        row.action: row.payload for row in (await db_session.execute(select(AdminAuditLog))).scalars()
    }
    assert audits[ACTION_DEBUG_ZONE_CORRECTION_PLAYER]["removed"] == [EARLY]
    assert audits[ACTION_DEBUG_ZONE_CORRECTION_PLAYER]["level"] == [1, 0]
    assert audits[ACTION_DEBUG_ZONE_CORRECTION]["backup"] == ARCHIVE


@pytest.mark.asyncio
async def test_a_second_run_finds_nothing_left(client, db_session, backups):
    await _alice(client, db_session)
    assert (await client.post(APPLY, json=await _confirmation(client))).status_code == 200
    again = (await client.get(SIMULATE)).json()
    assert (again["removed_total"], again["players_affected"]) == (0, 0)
    resp = await client.post(APPLY, json={"timezone": again["timezone"], "plan": again["plan"]})
    assert resp.json()["applied"]["players"] == 0
    assert backups[0] == ["zone_correction"]


@pytest.mark.asyncio
async def test_a_plan_the_admin_has_not_seen_is_refused(client, db_session, backups):
    alice = await _alice(client, db_session)
    resp = await client.post(APPLY, json={"timezone": "Europe/Paris", "plan": "0123456789abcdef"})
    assert (resp.status_code, resp.json()["detail"]) == (409, "plan_changed")
    assert await unlocked(db_session, alice) == {EARLY}
    assert backups[0] == []


@pytest.mark.asyncio
async def test_nothing_is_written_without_a_full_backup(client, db_session, backups):
    alice = await _alice(client, db_session)
    backups[1].append("pg_dump")
    resp = await client.post(APPLY, json=await _confirmation(client))
    assert (resp.status_code, resp.json()["detail"]) == (409, "backup_incomplete")
    assert await unlocked(db_session, alice) == {EARLY}
    assert (await profile_of(db_session, alice)).xp == 110


@pytest.mark.asyncio
async def test_a_second_apply_is_refused_while_one_runs(client, db_session, backups):
    await _alice(client, db_session)
    confirmation = await _confirmation(client)
    async with _run._apply_lock:
        resp = await client.post(APPLY, json=confirmation)
    assert (resp.status_code, resp.json()["detail"]) == (409, "already_running")


@pytest.mark.asyncio
async def test_a_player_whose_writing_fails_is_left_whole(client, db_session, backups, monkeypatch):
    alice = await _alice(client, db_session)
    record = _run.record_audit

    async def failing_for_players(db, **kwargs):
        if kwargs["action"] == ACTION_DEBUG_ZONE_CORRECTION_PLAYER:
            raise RuntimeError("audit write failed")
        return await record(db, **kwargs)

    monkeypatch.setattr(_run, "record_audit", failing_for_players)
    resp = await client.post(APPLY, json=await _confirmation(client))
    assert resp.json()["applied"] == {"players": 0, "removed": 0, "xp_removed": 0, "failed": 1, "changed": 0}
    assert await unlocked(db_session, alice) == {EARLY}
    assert (await profile_of(db_session, alice)).xp == 110
    assert (await db_session.execute(select(XpLedger).where(XpLedger.user_id == alice))).first()


@pytest.mark.asyncio
async def test_a_player_who_would_lose_a_trophy_not_shown_is_left_whole(client, db_session, monkeypatch):
    alice = await _alice(client, db_session)
    await _hold_all(db_session, alice, *MOVIES[:4])
    bob = await player(db_session, "bob", xp=10)
    play(db_session, "bob", DAWN_UTC_ONLY)
    await hold(db_session, bob, EARLY)
    confirmation = await _confirmation(client)

    # Five trophies once the early bird is counted: Collector rests on it, and was not in the plan.
    _while_backing_up(monkeypatch, lambda db: _hold_all(db, alice, COLLECTOR))
    resp = await client.post(APPLY, json=confirmation)

    assert resp.json()["applied"] == {"players": 1, "removed": 1, "xp_removed": 40, "failed": 0, "changed": 1}
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
async def test_a_player_left_whole_does_not_keep_the_transaction_open(client, db_session):
    alice = await _alice(client, db_session)
    ctx = await build_context(db_session)
    with pytest.raises(_run._PlanGrew):
        await _run._apply_player(db_session, ctx, alice, set(), {})
    assert not db_session.in_transaction()


@pytest.mark.asyncio
async def test_a_player_who_would_lose_less_than_shown_is_still_corrected(client, db_session, monkeypatch):
    alice = await _alice(client, db_session)
    await _hold_all(db_session, alice, *MOVIES[:4], COLLECTOR)
    simulated = (await client.get(SIMULATE)).json()
    assert simulated["removed_total"] == 2
    confirmation = {"timezone": simulated["timezone"], "plan": simulated["plan"]}

    # A fifth trophy besides the early bird: Collector no longer rests on it.
    _while_backing_up(monkeypatch, lambda db: _hold_all(db, alice, MOVIES[4]))
    resp = await client.post(APPLY, json=confirmation)

    assert resp.json()["applied"] == {"players": 1, "removed": 1, "xp_removed": 40, "failed": 0, "changed": 0}
    assert await unlocked(db_session, alice) == {COLLECTOR, *MOVIES[:5]}


@pytest.mark.asyncio
async def test_a_player_with_nothing_left_to_take_is_not_counted_as_changed(client, db_session, monkeypatch):
    alice = await _alice(client, db_session)
    confirmation = await _confirmation(client)

    async def dawn_in_the_zone(db):
        play(db, "alice", DAWN_IN_PARIS)
        await db.commit()

    _while_backing_up(monkeypatch, dawn_in_the_zone)
    resp = await client.post(APPLY, json=confirmation)

    assert resp.json()["applied"] == {"players": 0, "removed": 0, "xp_removed": 0, "failed": 0, "changed": 0}
    assert await unlocked(db_session, alice) == {EARLY}
    assert await _player_audits(db_session) == []


@pytest.mark.asyncio
async def test_xp_never_falls_below_zero(client, db_session, backups):
    alice = await _alice(client, db_session)
    profile = await profile_of(db_session, alice)
    profile.xp = 15  # drifted below the trophy's own 40
    await db_session.commit()
    assert (await client.post(APPLY, json=await _confirmation(client))).status_code == 200
    assert (await profile_of(db_session, alice)).xp == 0


@pytest.mark.asyncio
async def test_unknown_fields_are_refused(client, db_session, backups):
    await _alice(client, db_session)
    body = {**await _confirmation(client), "force": True}
    assert (await client.post(APPLY, json=body)).status_code == 422
