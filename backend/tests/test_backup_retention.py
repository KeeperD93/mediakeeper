"""Retention dispatch shared by the manual endpoint and the scheduled handler.

A negative ``backup.retention_days`` means "keep the N most recent" (count); a
positive value means "delete older than N days". Both paths route through
``apply_retention_for_setting`` so the scheduled auto-backup honours the count
policy the manual button already did.
"""
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.backup import _crud
from api.backup._schemas import BackupRequest
from services.backup import apply_retention_for_setting
from services.settings import set_setting


def _make_backup(dir_: Path, name: str, age_days: float = 0) -> Path:
    f = dir_ / f"mediakeeper_backup_{name}.zip"
    f.write_bytes(b"x")
    if age_days:
        past = time.time() - age_days * 86400
        os.utime(f, (past, past))
    return f


def test_negative_retention_keeps_n_most_recent(tmp_path):
    for i in range(5):
        _make_backup(tmp_path, f"f{i}", age_days=5 - i)  # f4 newest, f0 oldest

    removed = apply_retention_for_setting(-2, tmp_path)

    assert removed == 3
    remaining = {p.name for p in tmp_path.glob("mediakeeper_backup_*.zip")}
    assert remaining == {"mediakeeper_backup_f4.zip", "mediakeeper_backup_f3.zip"}


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
        return new

    monkeypatch.setattr(_crud, "create_backup", _fake_create)
    monkeypatch.setattr(_crud, "resolve_backup_dir", AsyncMock(return_value=backup_dir))

    resp = await _crud.create_backup_endpoint(
        BackupRequest(), db=db_session, _=SimpleNamespace(username="tester"),
    )

    assert resp["success"] is True
    remaining = {p.name for p in backup_dir.glob("mediakeeper_backup_*.zip")}
    assert remaining == {"mediakeeper_backup_new.zip", "mediakeeper_backup_old3.zip"}
