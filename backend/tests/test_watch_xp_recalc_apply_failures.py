"""Applying the watch XP recalculation when something is wrong: a plan the admin has not
seen, a backup missing a part or failing, an error while writing, a row the database
refuses, a commit that fails to answer, a request cancelled during its commit. Nothing of
the plan is written, but maybe by that commit."""
import asyncio
import logging
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from models.portal.xp_ledger import XpLedger
from services.backup.create import BackupResult
from services.portal import daily_digest
from services.portal.admin_users_constants import (
    ACTION_DEBUG_WATCH_XP_RECALC,
    ACTION_DEBUG_WATCH_XP_RECALC_PLAYER,
)
from services.portal.recalc_lock import RECALC_LOCK
from services.portal.watch_xp_recalc import _run
from tests._watch_xp_apply_helpers import (
    APPLY,
    ARCHIVE,
    HOUR,
    audit_rows,
    confirmation,
    fake_backups,
    ledger_rows,
    snapshot,
    two_players,
)
from tests._watch_xp_helpers import T, watched

pytestmark = pytest.mark.asyncio


@pytest.fixture
def backups(monkeypatch):
    return fake_backups(monkeypatch)


def _lost(what: str) -> OperationalError:
    """What a statement raises when the connection drops under it."""
    return OperationalError(what, None, ConnectionResetError("connection reset by peer"))


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
    assert "journal of the error may be missing" in caplog.text


async def test_a_row_the_database_refuses_is_refused_as_failed_before_the_commit(
    client, db_session, backups, monkeypatch, caplog,
):
    db = db_session
    ids = await two_players(client, db)
    confirmed = await confirmation(client)
    before = await snapshot(db)
    record = _run.record_audit

    async def twin_with_the_overall_journal(db, **kwargs):
        entry = await record(db, **kwargs)
        if kwargs["action"] == ACTION_DEBUG_WATCH_XP_RECALC and not kwargs["commit"]:
            # The last write before the rows are sent, whoever is written last: the twin of
            # Alice's sign-in, which the recalculation leaves alone, breaks the unique key.
            db.add(XpLedger(user_id=ids["alice"], action="daily_login", reference="2026-03-07", xp=2, created_at=T))
        return entry

    monkeypatch.setattr(_run, "record_audit", twin_with_the_overall_journal)
    with caplog.at_level(logging.ERROR, logger=_run.logger.name):
        resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "apply_failed")
    assert (await snapshot(db))[:2] == before[:2]
    (failure,) = (await audit_rows(db))[ACTION_DEBUG_WATCH_XP_RECALC]
    assert failure.payload == {**confirmed, "backup": ARCHIVE, "failed": True}
    assert "IntegrityError" in caplog.text
    assert f"nothing written; backup {ARCHIVE}" in caplog.text


async def test_a_failure_whose_rollback_fails_is_still_refused_as_failed(
    client, db_session, backups, monkeypatch, caplog,
):
    db = db_session
    await two_players(client, db)
    confirmed = await confirmation(client)
    before = await snapshot(db)
    record = _run.record_audit

    async def player_write_lost(db, **kwargs):
        if kwargs["action"] == ACTION_DEBUG_WATCH_XP_RECALC_PLAYER:
            async def rollback_lost():
                del db.rollback
                raise _lost("ROLLBACK")

            db.rollback = rollback_lost
            raise _lost("INSERT")
        return await record(db, **kwargs)

    monkeypatch.setattr(_run, "record_audit", player_write_lost)
    with caplog.at_level(logging.ERROR, logger=_run.logger.name):
        resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "apply_failed")
    assert await snapshot(db) == before
    assert "journal of the error may be missing" in caplog.text


def _commit_without_answer(monkeypatch, *, reached: bool) -> list[dict]:
    """The commit of the apply fails to answer, after reaching the database or before; returns
    what the digest cache holds each time the commit is sent."""
    record, at_commit = _run.record_audit, []

    async def recording(db, **kwargs):
        entry = await record(db, **kwargs)
        if kwargs["action"] == ACTION_DEBUG_WATCH_XP_RECALC and "uncertain" not in kwargs["payload"]:
            real_commit = db.commit  # the overall journal is the last write before the commit

            async def lost_answer():
                del db.commit
                at_commit.append(dict(daily_digest._digest_cache))
                if reached:
                    await real_commit()
                raise _lost("COMMIT")

            db.commit = lost_answer
        return entry

    monkeypatch.setattr(_run, "record_audit", recording)
    return at_commit


@pytest.mark.parametrize("reached", [True, False], ids=["written", "not_written"])
async def test_a_commit_that_fails_to_answer_is_refused_as_uncertain(
    client, db_session, backups, monkeypatch, caplog, reached,
):
    db = db_session
    ids = await two_players(client, db)
    confirmed = await confirmation(client)
    before = await ledger_rows(db)
    monkeypatch.setattr(daily_digest, "_digest_cache", {})  # holds nothing but Alice's digest
    daily_digest._cache_set(ids["alice"], "2026-03-08", "fr", {"cached": True})
    at_commit = _commit_without_answer(monkeypatch, reached=reached)
    journal_error, seen = _run._journal_error, []

    async def journal_seeing_the_cache(db, payload, audit):
        seen.append(dict(daily_digest._digest_cache))
        await journal_error(db, payload, audit)

    monkeypatch.setattr(_run, "_journal_error", journal_seeing_the_cache)
    with caplog.at_level(logging.ERROR, logger=_run.logger.name):
        resp = await client.post(APPLY, json=confirmed)

    assert (resp.status_code, resp.json()["detail"]) == (409, "apply_uncertain")
    assert [len(cache) for cache in at_commit] == [1]  # Alice's digest stays until the commit is sent
    assert seen == [{}]  # the digests went before the journal, which a lost connection may hold up
    assert (await ledger_rows(db) != before) is reached
    overall = [row.payload for row in (await audit_rows(db))[ACTION_DEBUG_WATCH_XP_RECALC]]
    assert ["uncertain" in payload for payload in overall] == ([False, True] if reached else [True])
    assert overall[-1] == {**confirmed, "backup": ARCHIVE, "uncertain": True}
    assert f"commit outcome unknown; backup {ARCHIVE}" in caplog.text
    assert daily_digest._digest_cache == {}


async def test_a_request_cancelled_during_its_commit_drops_the_cached_digests(
    client, db_session, backups, monkeypatch,
):
    db = db_session
    ids = await two_players(client, db)
    confirmed = await confirmation(client)
    before = await ledger_rows(db)
    monkeypatch.setattr(daily_digest, "_digest_cache", {})  # left as it was, whatever the outcome
    daily_digest._cache_set(ids["alice"], "2026-03-08", "fr", {"cached": True})
    record, committed = _run.record_audit, asyncio.Event()

    async def recording(db, **kwargs):
        entry = await record(db, **kwargs)
        if kwargs["action"] == ACTION_DEBUG_WATCH_XP_RECALC:
            real_commit = db.commit  # the overall journal is the last write before the commit

            async def commit_then_wait():
                del db.commit
                await real_commit()
                committed.set()
                await asyncio.sleep(30)  # cancelled long before

            db.commit = commit_then_wait
        return entry

    monkeypatch.setattr(_run, "record_audit", recording)
    request = asyncio.create_task(client.post(APPLY, json=confirmed))
    await asyncio.wait_for(committed.wait(), 10)
    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(request, 10)

    assert await ledger_rows(db) != before
    assert daily_digest._digest_cache == {}
    assert not RECALC_LOCK.locked()
