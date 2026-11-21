"""Applying the watch XP recalculation: the plan the admin saw, a full backup first, every
player written in one transaction, and nothing written when anything goes wrong."""
import asyncio
from datetime import UTC, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from models.portal.audit import AdminAuditLog
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from services.backup.create import BackupResult
from services.portal import daily_digest
from services.portal.admin_users_constants import (
    ACTION_DEBUG_WATCH_XP_RECALC,
    ACTION_DEBUG_WATCH_XP_RECALC_PLAYER,
)
from services.portal.watch_xp_recalc import _run
from services.portal.xp import completion_reference
from services.portal.zone_correction import _run as zone_run
from tests._watch_xp_helpers import T, account, watched
from tests._watch_xp_recalc_helpers import give, sign_in_as, sitting

pytestmark = pytest.mark.asyncio
SIMULATE = "/api/portal/admin/debug/watch-xp/simulate"
APPLY = "/api/portal/admin/debug/watch-xp/apply"
ARCHIVE = "mediakeeper_backup_20260308_120000_watch_xp_recalc.zip"
HOUR = timedelta(hours=1)


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


async def _two_players(client, db) -> dict[str, int]:
    """Alice: a film paid by the former rule and never finished, a sign-in, 270 XP from
    before the ledger and a film watched to its end. Bob: an episode watched to its end."""
    await sign_in_as(client, db, "admin", "admin")
    alice, bob = await account(db, "alice"), await account(db, "bob")
    await sitting(db, "alice", "MOVIE-9", T - 3 * HOUR)
    await give(db, alice, "watch_movie", "MOVIE-9:2026-03-07", 10, T - 2 * HOUR)
    await give(db, alice, "daily_login", "2026-03-07", 2, T - 2 * HOUR)
    profile = await _profile(db, alice)
    profile.xp += 270
    await db.commit()
    film = await watched(db, "alice", at=T - HOUR)  # 2 h: 40
    episode = await watched(db, "bob", item="EP-1", item_type="Episode", runtime=2700, at=T + HOUR)  # 15
    return {"alice": alice, "bob": bob, "film": film, "episode": episode}


async def _profile(db, user_id: int) -> UserProfile:
    query = select(UserProfile).where(UserProfile.user_id == user_id).execution_options(populate_existing=True)
    return (await db.execute(query)).scalar_one()


async def _confirmation(client) -> dict:
    simulated = (await client.get(SIMULATE)).json()
    return {"as_of": simulated["as_of"], "plan": simulated["plan"]}


async def _ledger(db) -> dict[int, list[tuple]]:
    rows = (await db.execute(
        select(XpLedger.user_id, XpLedger.action, XpLedger.reference, XpLedger.xp, XpLedger.created_at)
        .order_by(XpLedger.user_id, XpLedger.reference)
    )).all()
    found: dict[int, list[tuple]] = {}
    for user_id, action, reference, xp, at in rows:
        found.setdefault(user_id, []).append((action, reference, xp, at.replace(tzinfo=UTC) if at.tzinfo is None else at))
    return found


async def _state(db) -> tuple:
    profiles = (await db.execute(select(UserProfile.user_id, UserProfile.xp, UserProfile.level))).all()
    audits = (await db.execute(select(AdminAuditLog.action))).scalars().all()
    return await _ledger(db), sorted(profiles), audits


async def _audits(db) -> dict[str, list[AdminAuditLog]]:
    found: dict[str, list[AdminAuditLog]] = {}
    for row in (await db.execute(select(AdminAuditLog).order_by(AdminAuditLog.id))).scalars():
        found.setdefault(row.action, []).append(row)
    return found


async def test_apply_writes_the_rows_at_their_date_and_journals_each_player(client, db_session, backups):
    db = db_session
    ids = await _two_players(client, db)
    alice, bob = ids["alice"], ids["bob"]
    daily_digest._cache_set(alice, "2026-03-08", "fr", {"cached": True})
    confirmed = await _confirmation(client)

    resp = await client.post(APPLY, json=confirmed)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "plan": confirmed["plan"], "backup": ARCHIVE,
        "applied": {"players": 2, "rows_deleted": 1, "rows_inserted": 2},
    }
    assert backups[0] == ["watch_xp_recalc"]
    film, episode = completion_reference("MOVIE-1", ids["film"]), completion_reference("EP-1", ids["episode"])
    assert await _ledger(db) == {
        alice: [("daily_login", "2026-03-07", 2, T - 2 * HOUR), ("watch_movie", film, 40, T - HOUR)],
        bob: [("watch_episode", episode, 15, T + HOUR)],
    }
    # XP: before, less what went, plus what came; the 270 from before the ledger stay.
    assert [((p := await _profile(db, user_id)).xp, p.level) for user_id in (alice, bob)] == [(312, 2), (15, 1)]
    assert daily_digest._digest_cache == {}

    audits = await _audits(db)
    players = {row.target_user_id: row.payload for row in audits[ACTION_DEBUG_WATCH_XP_RECALC_PLAYER]}
    assert players[alice] == {
        "xp": [282, 312], "level": [1, 2],
        "undo": {
            "deleted": [{
                "action": "watch_movie", "reference": "MOVIE-9:2026-03-07", "xp": 10,
                "created_at": (T - 2 * HOUR).isoformat(),
            }],
            "inserted": [film],
        },
    }
    assert players[bob]["undo"] == {"deleted": [], "inserted": [episode]}
    (overall,) = audits[ACTION_DEBUG_WATCH_XP_RECALC]
    assert overall.target_user_id is None
    assert overall.payload == {
        "as_of": confirmed["as_of"], "plan": confirmed["plan"], "backup": ARCHIVE,
        "players": 2, "rows_deleted": 1, "rows_inserted": 2,
    }


async def test_a_second_run_finds_nothing_and_backs_nothing_up(client, db_session, backups):
    await _two_players(client, db_session)
    assert (await client.post(APPLY, json=await _confirmation(client))).status_code == 200

    again = (await client.get(SIMULATE)).json()
    assert again["players_changed"] == 0
    resp = await client.post(APPLY, json={"as_of": again["as_of"], "plan": again["plan"]})

    assert resp.json() == {
        "plan": again["plan"], "backup": None, "applied": {"players": 0, "rows_deleted": 0, "rows_inserted": 0},
    }
    assert backups[0] == ["watch_xp_recalc"]


async def test_a_moment_without_zone_is_read_as_utc(client, db_session, backups):
    await _two_players(client, db_session)
    confirmed = await _confirmation(client)
    naive = confirmed["as_of"].removesuffix("+00:00")
    assert naive != confirmed["as_of"]

    resp = await client.post(APPLY, json={**confirmed, "as_of": naive})

    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"]["players"] == 2


async def test_a_plan_the_admin_has_not_seen_is_refused(client, db_session, backups):
    await _two_players(client, db_session)
    confirmed = await _confirmation(client)
    before = await _state(db_session)

    resp = await client.post(APPLY, json={**confirmed, "plan": "0123456789abcdef"})

    assert (resp.status_code, resp.json()["detail"]) == (409, "plan_changed")
    assert await _state(db_session) == before
    assert backups[0] == []


async def test_nothing_is_written_without_a_full_backup(client, db_session, backups):
    await _two_players(client, db_session)
    confirmed = await _confirmation(client)
    before = await _state(db_session)
    backups[1].append("pg_dump")

    resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "backup_incomplete")
    assert await _state(db_session) == before


async def test_a_plan_that_changed_during_the_backup_is_refused_under_the_locks(client, db_session, monkeypatch):
    db = db_session
    await _two_players(client, db)
    confirmed = await _confirmation(client)

    async def backup_while_a_title_is_watched(db, label=""):
        await watched(db, "bob", item="EP-2", item_type="Episode", runtime=2700, at=T + 2 * HOUR)
        return BackupResult(Path(ARCHIVE))

    monkeypatch.setattr(_run, "create_backup", backup_while_a_title_is_watched)
    before = await _state(db)

    resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "plan_changed")
    assert await _state(db) == before  # the watched title was saved, nothing of the plan


async def test_an_error_midway_writes_nothing_and_journals_the_backup(client, db_session, backups, monkeypatch):
    db = db_session
    await _two_players(client, db)
    confirmed = await _confirmation(client)
    before = await _state(db)
    record, players = _run.record_audit, []

    async def failing_on_the_second_player(db, **kwargs):
        if kwargs["action"] == ACTION_DEBUG_WATCH_XP_RECALC_PLAYER:
            players.append(kwargs["target_user_id"])
            if len(players) == 2:
                raise RuntimeError("audit write failed")
        return await record(db, **kwargs)

    monkeypatch.setattr(_run, "record_audit", failing_on_the_second_player)

    resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "apply_failed")
    assert len(players) == 2  # the first player was written, then taken back
    ledger, profiles, audits = await _state(db)
    assert (ledger, profiles) == before[:2]
    assert audits == [ACTION_DEBUG_WATCH_XP_RECALC]
    (failure,) = (await _audits(db))[ACTION_DEBUG_WATCH_XP_RECALC]
    assert failure.payload == {"as_of": confirmed["as_of"], "plan": confirmed["plan"], "backup": ARCHIVE, "failed": True}


async def test_an_apply_is_refused_while_a_time_zone_correction_runs(client, db_session, backups):
    await _two_players(client, db_session)
    confirmed = await _confirmation(client)

    async with zone_run._apply_lock:
        # Bounded: an apply that waited for the lock instead of refusing would hang the test.
        resp = await asyncio.wait_for(client.post(APPLY, json=confirmed), timeout=10)

    assert (resp.status_code, resp.json()["detail"]) == (409, "already_running")
    assert backups[0] == []


async def test_a_viewer_cannot_apply(client, db_session):
    await sign_in_as(client, db_session, "bob", "viewer")

    assert (await client.post(APPLY, json={"as_of": T.isoformat(), "plan": "x"})).status_code == 403


async def test_unknown_fields_are_refused(client, db_session, backups):
    await _two_players(client, db_session)

    assert (await client.post(APPLY, json={**await _confirmation(client), "force": True})).status_code == 422
