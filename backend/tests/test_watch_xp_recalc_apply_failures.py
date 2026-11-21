"""Applying the watch XP recalculation when something is wrong: a plan the admin has not
seen, a backup missing a part or failing, an error while writing. Nothing of the plan is
written."""
import logging
from pathlib import Path

import pytest

from services.backup.create import BackupResult
from services.portal.admin_users_constants import (
    ACTION_DEBUG_WATCH_XP_RECALC,
    ACTION_DEBUG_WATCH_XP_RECALC_PLAYER,
)
from services.portal.watch_xp_recalc import _run
from tests._watch_xp_apply_helpers import (
    APPLY,
    ARCHIVE,
    HOUR,
    audit_rows,
    confirmation,
    fake_backups,
    snapshot,
    two_players,
)
from tests._watch_xp_helpers import T, watched

pytestmark = pytest.mark.asyncio


@pytest.fixture
def backups(monkeypatch):
    return fake_backups(monkeypatch)


async def test_a_plan_the_admin_has_not_seen_is_refused(client, db_session, backups):
    await two_players(client, db_session)
    confirmed = await confirmation(client)
    before = await snapshot(db_session)

    resp = await client.post(APPLY, json={**confirmed, "plan": "0123456789abcdef"})

    assert (resp.status_code, resp.json()["detail"]) == (409, "plan_changed")
    assert await snapshot(db_session) == before
    assert backups[0] == []


async def test_nothing_is_written_without_a_full_backup(client, db_session, backups):
    await two_players(client, db_session)
    confirmed = await confirmation(client)
    before = await snapshot(db_session)
    backups[1].append("pg_dump")

    resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "backup_incomplete")
    assert await snapshot(db_session) == before


async def test_a_backup_that_fails_refuses_the_apply_as_incomplete(client, db_session, monkeypatch, caplog):
    await two_players(client, db_session)
    confirmed = await confirmation(client)
    before = await snapshot(db_session)

    async def disk_full(db, label=""):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(_run, "create_backup", disk_full)
    with caplog.at_level(logging.ERROR, logger=_run.logger.name):
        resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "backup_incomplete")
    assert await snapshot(db_session) == before
    assert "backup failed: nothing applied" in caplog.text


async def test_a_plan_that_changed_during_the_backup_is_refused_by_the_second_check(client, db_session, monkeypatch):
    db = db_session
    await two_players(client, db)
    confirmed = await confirmation(client)

    async def backup_while_a_title_is_watched(db, label=""):
        await watched(db, "bob", item="EP-2", item_type="Episode", runtime=2700, at=T + 2 * HOUR)
        return BackupResult(Path(ARCHIVE))

    monkeypatch.setattr(_run, "create_backup", backup_while_a_title_is_watched)
    before = await snapshot(db)

    resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "plan_changed")
    assert await snapshot(db) == before  # the watched title was saved, nothing of the plan


async def test_an_error_midway_writes_nothing_and_journals_the_backup(client, db_session, backups, monkeypatch):
    db = db_session
    await two_players(client, db)
    confirmed = await confirmation(client)
    before = await snapshot(db)
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
    ledger, profiles, actions = await snapshot(db)
    assert (ledger, profiles) == before[:2]
    assert actions == [ACTION_DEBUG_WATCH_XP_RECALC]
    (failure,) = (await audit_rows(db))[ACTION_DEBUG_WATCH_XP_RECALC]
    assert failure.payload == {"as_of": confirmed["as_of"], "plan": confirmed["plan"], "backup": ARCHIVE, "failed": True}


async def test_a_failure_journal_that_fails_still_refuses_the_apply_as_failed(
    client, db_session, backups, monkeypatch, caplog,
):
    db = db_session
    await two_players(client, db)
    confirmed = await confirmation(client)
    before = await snapshot(db)
    record = _run.record_audit

    async def connection_lost(db, **kwargs):
        if kwargs["action"] == ACTION_DEBUG_WATCH_XP_RECALC_PLAYER or kwargs["payload"].get("failed"):
            raise RuntimeError("connection lost")
        return await record(db, **kwargs)

    monkeypatch.setattr(_run, "record_audit", connection_lost)
    with caplog.at_level(logging.ERROR, logger=_run.logger.name):
        resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "apply_failed")
    assert await snapshot(db) == before
    assert f"nothing written; backup {ARCHIVE}" in caplog.text
    assert "failure journal not written" in caplog.text
