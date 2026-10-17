"""Retention policy shared by every backup path.

A negative ``backup.retention_days`` means "keep the N most recent" (count); a
positive value means "delete older than N days". The manual backup, the "apply
now" button and the scheduled auto-backup all go through
``apply_configured_retention`` so they can't diverge. The API only stores the
values the settings screen offers.
"""
import logging
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.backup import _crud, _retention
from api.backup._schemas import BackupRequest
from services.backup import BackupResult, apply_retention_for_setting, get_retention_days
from services.scheduler._handlers import _handler_backup
from services.settings import set_setting

ADMIN = SimpleNamespace(username="tester")


def _make_backup(dir_: Path, name: str, age_days: float = 0) -> Path:
    f = dir_ / f"mediakeeper_backup_{name}.zip"
    f.write_bytes(b"x")
    if age_days:
        past = time.time() - age_days * 86400
        os.utime(f, (past, past))
    return f


def _remaining(dir_: Path) -> set[str]:
    return {p.name for p in dir_.glob("mediakeeper_backup_*.zip")}


def test_negative_retention_keeps_n_most_recent(tmp_path):
    for i in range(5):
        _make_backup(tmp_path, f"f{i}", age_days=5 - i)  # f4 newest, f0 oldest

    removed = apply_retention_for_setting(-2, tmp_path)

    assert removed == 3
    assert _remaining(tmp_path) == {"mediakeeper_backup_f4.zip", "mediakeeper_backup_f3.zip"}


def test_positive_retention_deletes_older_than_days(tmp_path):
    _make_backup(tmp_path, "old", age_days=40)
    _make_backup(tmp_path, "fresh", age_days=1)

    removed = apply_retention_for_setting(30, tmp_path)

    assert removed == 1
    assert (tmp_path / "mediakeeper_backup_fresh.zip").exists()
    assert not (tmp_path / "mediakeeper_backup_old.zip").exists()


def test_zero_retention_is_noop(tmp_path):
    _make_backup(tmp_path, "keep", age_days=100)

    assert apply_retention_for_setting(0, tmp_path) == 0
    assert (tmp_path / "mediakeeper_backup_keep.zip").exists()


def test_absurd_day_count_keeps_everything(tmp_path):
    """A value stored before the API had bounds must not crash the cleanup."""
    _make_backup(tmp_path, "old", age_days=40)

    assert apply_retention_for_setting(10**9, tmp_path) == 0
    assert _remaining(tmp_path) == {"mediakeeper_backup_old.zip"}


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [366, -101])
async def test_retention_outside_the_screen_bounds_is_refused(authed_client, db_session, days):
    resp = await authed_client.post("/api/backup/retention", json={"days": days})

    assert resp.status_code == 422
    assert await get_retention_days(db_session) == 30


@pytest.mark.asyncio
async def test_retention_is_stored_where_every_backup_path_reads_it(authed_client, db_session):
    resp = await authed_client.post("/api/backup/retention", json={"days": -3})

    assert resp.json() == {"success": True, "days": -3}
    assert await get_retention_days(db_session) == -3


@pytest.mark.asyncio
async def test_retention_defaults_to_30_days_until_configured(db_session):
    assert await get_retention_days(db_session) == 30
    await set_setting(db_session, "backup.retention_days", "-2")
    assert await get_retention_days(db_session) == -2


@pytest.mark.asyncio
async def test_manual_create_applies_retention(db_session, workspace_tmp_path, monkeypatch):
    """The manual /create endpoint enforces retention immediately, like the
    scheduled backup — otherwise manual backups pile up until the next auto run."""
    backup_dir = Path(workspace_tmp_path)
    await set_setting(db_session, "backup.retention_days", "-2")  # keep the 2 most recent

    for name, age in (("old1", 3), ("old2", 2), ("old3", 1)):
        _make_backup(backup_dir, name, age_days=age)

    new = backup_dir / "mediakeeper_backup_new.zip"

    async def _fake_create(db, components=None, label=""):
        new.write_bytes(b"x")  # newest backup (mtime now)
        return BackupResult(new)

    monkeypatch.setattr(_crud, "create_backup", _fake_create)
    monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

    resp = await _crud.create_backup_endpoint(BackupRequest(), db=db_session, _=ADMIN)

    assert resp["success"] is True
    assert _remaining(backup_dir) == {"mediakeeper_backup_new.zip", "mediakeeper_backup_old3.zip"}


@pytest.mark.asyncio
async def test_manual_create_survives_retention_failure(db_session, workspace_tmp_path, monkeypatch):
    """A retention cleanup failure after a successful backup is logged, not fatal —
    the endpoint still reports success rather than a misleading 500."""
    new = Path(workspace_tmp_path) / "mediakeeper_backup_new.zip"

    async def _fake_create(db, components=None, label=""):
        new.write_bytes(b"x")
        return BackupResult(new)

    monkeypatch.setattr(_crud, "create_backup", _fake_create)
    monkeypatch.setattr(
        _crud, "apply_configured_retention", AsyncMock(side_effect=PermissionError("nas locked")),
    )

    resp = await _crud.create_backup_endpoint(BackupRequest(), db=db_session, _=ADMIN)

    assert resp["success"] is True
    assert resp["filename"] == "mediakeeper_backup_new.zip"


@pytest.mark.asyncio
async def test_incomplete_manual_backup_is_reported_and_keeps_older_ones(
    db_session, workspace_tmp_path, monkeypatch,
):
    """A backup missing a part must not push complete ones out of a keep-N window."""
    backup_dir = Path(workspace_tmp_path)
    await set_setting(db_session, "backup.retention_days", "-1")
    _make_backup(backup_dir, "complete", age_days=1)
    new = backup_dir / "mediakeeper_backup_new.zip"

    async def _fake_create(db, components=None, label=""):
        new.write_bytes(b"x")
        return BackupResult(new, ("pg_dump",))

    monkeypatch.setattr(_crud, "create_backup", _fake_create)
    monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

    resp = await _crud.create_backup_endpoint(BackupRequest(), db=db_session, _=ADMIN)

    assert resp["failed_components"] == ["pg_dump"]
    assert _remaining(backup_dir) == {"mediakeeper_backup_new.zip", "mediakeeper_backup_complete.zip"}


@pytest.mark.asyncio
async def test_apply_now_reports_the_backups_removed(db_session, workspace_tmp_path, monkeypatch):
    backup_dir = Path(workspace_tmp_path)
    await set_setting(db_session, "backup.retention_days", "-1")
    _make_backup(backup_dir, "older", age_days=2)
    _make_backup(backup_dir, "newer", age_days=1)
    monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

    resp = await _retention.apply_retention_now(db=db_session, _=ADMIN)

    assert resp == {"success": True, "removed": 1}
    assert _remaining(backup_dir) == {"mediakeeper_backup_newer.zip"}


@pytest.mark.asyncio
async def test_scheduled_backup_applies_retention(db_session, workspace_tmp_path, monkeypatch):
    backup_dir = Path(workspace_tmp_path)
    await set_setting(db_session, "backup.retention_days", "-1")
    _make_backup(backup_dir, "previous", age_days=1)
    new = backup_dir / "mediakeeper_backup_auto.zip"

    async def _fake_create(db, components=None, label="", progress_cb=None):
        new.write_bytes(b"x")
        return BackupResult(new)

    monkeypatch.setattr("services.backup.create_backup", _fake_create)
    monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

    await _handler_backup(db_session)

    assert _remaining(backup_dir) == {"mediakeeper_backup_auto.zip"}


@pytest.mark.asyncio
async def test_incomplete_scheduled_backup_fails_the_task_and_keeps_older_ones(
    db_session, workspace_tmp_path, monkeypatch,
):
    backup_dir = Path(workspace_tmp_path)
    await set_setting(db_session, "backup.retention_days", "-1")
    _make_backup(backup_dir, "complete", age_days=1)
    new = backup_dir / "mediakeeper_backup_auto.zip"

    async def _fake_create(db, components=None, label="", progress_cb=None):
        new.write_bytes(b"x")
        return BackupResult(new, ("pg_dump",))

    monkeypatch.setattr("services.backup.create_backup", _fake_create)
    monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

    with pytest.raises(RuntimeError, match="without: pg_dump"):
        await _handler_backup(db_session)

    assert _remaining(backup_dir) == {"mediakeeper_backup_auto.zip", "mediakeeper_backup_complete.zip"}


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", ["{not json", "[1]"])
async def test_scheduled_backup_falls_back_on_unreadable_components(
    db_session, monkeypatch, caplog, stored,
):
    await set_setting(db_session, "backup.auto_components", stored)
    create = AsyncMock(return_value=BackupResult(Path("unused.zip")))
    monkeypatch.setattr("services.backup.create_backup", create)
    monkeypatch.setattr("services.backup.apply_configured_retention", AsyncMock(return_value=0))

    with caplog.at_level(logging.WARNING, logger="mediakeeper.scheduler"):
        await _handler_backup(db_session)

    assert create.await_args.kwargs["components"] == {}
    assert "unreadable backup.auto_components" in caplog.text


@pytest.mark.asyncio
async def test_info_lists_backups_with_the_configured_retention(db_session, workspace_tmp_path, monkeypatch):
    backup_dir = Path(workspace_tmp_path)
    _make_backup(backup_dir, "one")
    monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

    resp = await _crud.backup_info(db=db_session, _=ADMIN)

    assert resp["retention_days"] == 30
    assert [b["filename"] for b in resp["backups"]] == ["mediakeeper_backup_one.zip"]
