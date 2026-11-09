"""The correction endpoints: admin only, the plan the admin has seen, a full backup first."""
import logging
from pathlib import Path

import pytest
from sqlalchemy import select

from models.portal.achievement import UserAchievement
from models.portal.audit import AdminAuditLog
from models.portal.xp_ledger import XpLedger
from services.backup.create import BackupResult
from services.portal import daily_digest
from services.portal.achievements import seed_achievements
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ZONE_CORRECTION,
    ACTION_DEBUG_ZONE_CORRECTION_PLAYER,
)
from services.portal.zone_correction import _plan, _run
from tests._zone_correction_helpers import (
    APPLY,
    ARCHIVE,
    EARLY,
    SIMULATE,
    alice_with_early_bird,
    confirmation,
    freeze,
    profile_of,
    sign_in_as,
    unlocked,
)


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


@pytest.mark.asyncio
async def test_a_viewer_reaches_neither_endpoint(client, db_session):
    await sign_in_as(client, db_session, "bob", "viewer")
    assert (await client.get(SIMULATE)).status_code == 403
    assert (await client.post(APPLY, json={"timezone": "UTC", "plan": "x"})).status_code == 403


@pytest.mark.asyncio
async def test_nothing_is_simulated_before_a_zone_is_saved(client, db_session):
    await seed_achievements(db_session)
    await sign_in_as(client, db_session, "admin", "admin")
    resp = await client.get(SIMULATE)
    assert (resp.status_code, resp.json()["detail"]) == (409, "zone_not_chosen")


@pytest.mark.asyncio
async def test_apply_takes_back_the_trophy_its_xp_and_its_badge(client, db_session, backups):
    alice = await alice_with_early_bird(client, db_session)
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
    await alice_with_early_bird(client, db_session)
    assert (await client.post(APPLY, json=await confirmation(client))).status_code == 200
    again = (await client.get(SIMULATE)).json()
    assert (again["removed_total"], again["players_affected"]) == (0, 0)
    resp = await client.post(APPLY, json={"timezone": again["timezone"], "plan": again["plan"]})
    assert resp.json()["applied"]["players"] == 0
    assert backups[0] == ["zone_correction"]


@pytest.mark.asyncio
async def test_a_plan_the_admin_has_not_seen_is_refused(client, db_session, backups):
    alice = await alice_with_early_bird(client, db_session)
    resp = await client.post(APPLY, json={"timezone": "Europe/Paris", "plan": "0123456789abcdef"})
    assert (resp.status_code, resp.json()["detail"]) == (409, "plan_changed")
    assert await unlocked(db_session, alice) == {EARLY}
    assert backups[0] == []


@pytest.mark.asyncio
async def test_nothing_is_written_without_a_full_backup(client, db_session, backups):
    alice = await alice_with_early_bird(client, db_session)
    backups[1].append("pg_dump")
    resp = await client.post(APPLY, json=await confirmation(client))
    assert (resp.status_code, resp.json()["detail"]) == (409, "backup_incomplete")
    assert await unlocked(db_session, alice) == {EARLY}
    assert (await profile_of(db_session, alice)).xp == 110


@pytest.mark.asyncio
async def test_a_second_apply_is_refused_while_one_runs(client, db_session, backups):
    await alice_with_early_bird(client, db_session)
    confirmed = await confirmation(client)
    async with _run._apply_lock:
        resp = await client.post(APPLY, json=confirmed)
    assert (resp.status_code, resp.json()["detail"]) == (409, "already_running")


@pytest.mark.asyncio
async def test_a_player_whose_planning_fails_is_counted_and_named(client, db_session, monkeypatch, caplog):
    alice = await alice_with_early_bird(client, db_session)
    real = _plan.plan_player

    async def failing_for_alice(db, ctx, profile):
        if profile.user_id == alice:
            raise RuntimeError("planning failed")
        return await real(db, ctx, profile)

    monkeypatch.setattr(_plan, "plan_player", failing_for_alice)
    with caplog.at_level(logging.ERROR, logger=_plan.logger.name):
        body = (await client.get(SIMULATE)).json()
    assert body["players_failed"] == 1
    assert f"planning failed for player {alice}" in caplog.text


@pytest.mark.asyncio
async def test_a_player_whose_writing_fails_is_left_whole(client, db_session, backups, monkeypatch, caplog):
    alice = await alice_with_early_bird(client, db_session)
    record = _run.record_audit

    async def failing_for_players(db, **kwargs):
        if kwargs["action"] == ACTION_DEBUG_ZONE_CORRECTION_PLAYER:
            raise RuntimeError("audit write failed")
        return await record(db, **kwargs)

    monkeypatch.setattr(_run, "record_audit", failing_for_players)
    with caplog.at_level(logging.ERROR, logger=_run.logger.name):
        resp = await client.post(APPLY, json=await confirmation(client))
    assert resp.json()["applied"] == {"players": 0, "removed": 0, "xp_removed": 0, "failed": 1, "changed": 0}
    assert f"player {alice} not corrected" in caplog.text
    assert await unlocked(db_session, alice) == {EARLY}
    assert (await profile_of(db_session, alice)).xp == 110
    assert (await db_session.execute(select(XpLedger).where(XpLedger.user_id == alice))).first()


@pytest.mark.asyncio
async def test_xp_never_falls_below_zero(client, db_session, backups):
    alice = await alice_with_early_bird(client, db_session)
    profile = await profile_of(db_session, alice)
    profile.xp = 15  # drifted below the trophy's own 40
    await db_session.commit()
    assert (await client.post(APPLY, json=await confirmation(client))).status_code == 200
    assert (await profile_of(db_session, alice)).xp == 0


@pytest.mark.asyncio
async def test_unknown_fields_are_refused(client, db_session, backups):
    await alice_with_early_bird(client, db_session)
    body = {**await confirmation(client), "force": True}
    assert (await client.post(APPLY, json=body)).status_code == 422
