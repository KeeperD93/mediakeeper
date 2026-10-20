"""Backup file endpoints act only on existing backup archives: anything else
(missing backup, foreign file) is a 404 that leaves the directory untouched.
Listing, deletion and retention take turns on the files, and skip a backup the
other process removed meanwhile."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from services.backup import listing

BACKUP = "mediakeeper_backup_20260101_120000.zip"

FILE_OPERATIONS = {
    "list": lambda d: listing.list_backups(d),
    "delete": lambda d: listing.delete_backup(BACKUP, d),
    "retention by days": lambda d: listing.apply_retention(1, d),
    "retention by count": lambda d: listing.apply_retention_by_count(1, d),
}


def _backup(dir_: Path, stamp: str, age_days: float) -> Path:
    f = dir_ / f"mediakeeper_backup_{stamp}.zip"
    f.write_bytes(b"x")
    past = time.time() - age_days * 86400
    os.utime(f, (past, past))
    return f


def _vanish(monkeypatch, gone: Path) -> None:
    """The other process (web or worker) removes ``gone`` after the scan."""
    real_stat = Path.stat

    def stat(self, *args, **kwargs):
        if self.name == gone.name:
            raise FileNotFoundError(self)
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)


@pytest.fixture
def backup_dir(workspace_tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_PATH", str(workspace_tmp_path))
    return workspace_tmp_path


@pytest.mark.asyncio
async def test_delete_removes_the_backup(authed_client, backup_dir):
    (backup_dir / BACKUP).write_bytes(b"x")

    resp = await authed_client.delete(f"/api/backup/{BACKUP}")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert not (backup_dir / BACKUP).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", [BACKUP, "notes.zip"])
async def test_delete_refuses_missing_or_foreign_files(authed_client, backup_dir, filename):
    (backup_dir / "notes.zip").write_bytes(b"x")

    resp = await authed_client.delete(f"/api/backup/{filename}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "backup_not_found"
    assert (backup_dir / "notes.zip").exists()


@pytest.mark.asyncio
async def test_download_serves_the_backup(authed_client, backup_dir):
    (backup_dir / BACKUP).write_bytes(b"zip-bytes")

    resp = await authed_client.get(f"/api/backup/download/{BACKUP}")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert resp.content == b"zip-bytes"


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", [BACKUP, "notes.zip"])
async def test_download_refuses_missing_or_foreign_files(authed_client, backup_dir, filename):
    (backup_dir / "notes.zip").write_bytes(b"x")

    resp = await authed_client.get(f"/api/backup/download/{filename}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "backup_not_found"


@pytest.mark.parametrize("operation", FILE_OPERATIONS)
def test_file_operations_take_turns(tmp_path, operation):
    """Run from worker threads, none of them trips over a file another one
    just removed: each waits for the one in progress."""
    (tmp_path / BACKUP).write_bytes(b"x")

    with listing._FILES_LOCK:
        worker = threading.Thread(target=FILE_OPERATIONS[operation], args=(tmp_path,))
        worker.start()
        worker.join(timeout=0.2)
        assert worker.is_alive()

    worker.join(timeout=5)
    assert not worker.is_alive()


def test_listing_and_age_retention_skip_a_backup_removed_meanwhile(tmp_path, monkeypatch):
    gone = _backup(tmp_path, "20260101_000000", age_days=40)
    old = _backup(tmp_path, "20260102_000000", age_days=40)
    _vanish(monkeypatch, gone)

    assert [b["filename"] for b in listing.list_backups(tmp_path)] == [old.name]
    assert listing.apply_retention(30, tmp_path) == 1
    assert not old.exists()


def test_count_retention_skips_a_backup_removed_meanwhile(tmp_path, monkeypatch):
    gone = _backup(tmp_path, "20260101_000000", age_days=3)
    older = _backup(tmp_path, "20260102_000000", age_days=2)
    newer = _backup(tmp_path, "20260103_000000", age_days=1)
    _vanish(monkeypatch, gone)

    assert listing.apply_retention_by_count(1, tmp_path) == 1
    assert not older.exists()
    assert newer.exists()


def _removed_just_before(monkeypatch) -> None:
    """The other process deletes each backup right before this one does."""
    real_unlink = Path.unlink

    def unlink(self, missing_ok=False):
        real_unlink(self, missing_ok=True)
        return real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)


@pytest.mark.parametrize(("operation", "expected"), [
    ("delete", True),
    ("retention by days", 2),
    ("retention by count", 1),
])
def test_a_backup_removed_just_before_its_deletion_is_not_an_error(
    tmp_path, monkeypatch, operation, expected,
):
    _backup(tmp_path, "20260101_120000", age_days=40)
    _backup(tmp_path, "20260102_120000", age_days=41)
    _removed_just_before(monkeypatch)

    assert FILE_OPERATIONS[operation](tmp_path) == expected
