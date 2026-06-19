"""Retention dispatch shared by the manual endpoint and the scheduled handler.

A negative ``backup.retention_days`` means "keep the N most recent" (count); a
positive value means "delete older than N days". Both paths route through
``apply_retention_for_setting`` so the scheduled auto-backup honours the count
policy the manual button already did.
"""
import os
import time
from pathlib import Path

from services.backup import apply_retention_for_setting


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
