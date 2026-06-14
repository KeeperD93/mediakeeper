import shutil
import uuid
from pathlib import Path

import pytest

from services import backup as backup_service
from services.path_config import get_backup_dir
from services.settings import set_setting


def _make_workspace_tmp() -> Path:
    root = Path(__file__).resolve().parent / "_tmp_backup_paths" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_set_backup_directory_rejects_when_locked_by_compose(monkeypatch):
    root = _make_workspace_tmp()
    try:
        compose_backup_dir = root / "compose-backups"
        monkeypatch.setenv("BACKUP_PATH", str(compose_backup_dir))

        with pytest.raises(ValueError, match="BACKUP_PATH"):
            backup_service.set_backup_directory(str(root / "other-backups"))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_set_backup_directory_accepts_path_inside_configured_roots(monkeypatch):
    root = _make_workspace_tmp()
    try:
        mounted_root = root / "mounted"
        mounted_root.mkdir()
        target = mounted_root / "backups" / "daily"

        monkeypatch.delenv("BACKUP_PATH", raising=False)
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(mounted_root))

        # Validates and creates the directory; persistence is the endpoint's job
        # (set_setting), no per-process cache is mutated.
        backup_service.set_backup_directory(str(target))

        assert target.exists()
        assert target.is_dir()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_set_backup_directory_rejects_path_outside_configured_roots(monkeypatch):
    root = _make_workspace_tmp()
    try:
        mounted_root = root / "mounted"
        mounted_root.mkdir()
        outside_parent = root / "elsewhere"
        outside_parent.mkdir()
        outside_target = outside_parent / "backups"

        monkeypatch.delenv("BACKUP_PATH", raising=False)
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(mounted_root))

        with pytest.raises(ValueError, match="MEDIAKEEPER_PATH_ROOTS|BACKUP_PATH"):
            backup_service.set_backup_directory(str(outside_target))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_list_available_backup_dirs_includes_configured_roots_and_env_backup(monkeypatch):
    root = _make_workspace_tmp()
    try:
        mounted_root = root / "mounted"
        mounted_root.mkdir()
        configured_backup_dir = root / "configured-backups"

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(mounted_root))
        monkeypatch.setenv("BACKUP_PATH", str(configured_backup_dir))

        directories = backup_service.list_available_backup_dirs(get_backup_dir())

        assert str(mounted_root.resolve()) in directories
        assert str(configured_backup_dir.resolve()) in directories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_backup_path_rejects_non_backup_zip_names():
    root = _make_workspace_tmp()
    try:
        backup_dir = root / "backups"
        backup_dir.mkdir()
        (backup_dir / "manual.zip").write_text("not a backup", encoding="utf-8")
        valid = backup_dir / "mediakeeper_backup_20260429_010203.zip"
        valid.write_text("backup", encoding="utf-8")

        assert backup_service.get_backup_path("manual.zip", backup_dir) is None
        assert (
            backup_service.get_backup_path(
                "../mediakeeper_backup_20260429_010203.zip", backup_dir
            )
            is None
        )
        assert backup_service.get_backup_path(valid.name, backup_dir) == valid.resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_resolve_backup_dir_reads_db_setting(db_session, monkeypatch):
    """No per-process cache: the worker resolves the directory the web process
    saved to the DB, even though it never called set_backup_directory itself."""
    custom = _make_workspace_tmp() / "custom-backups"
    try:
        monkeypatch.delenv("BACKUP_PATH", raising=False)  # unlocked → DB override is honoured
        await set_setting(db_session, "backup.directory", str(custom))
        assert await backup_service.resolve_backup_dir(db_session) == custom
    finally:
        shutil.rmtree(custom.parent, ignore_errors=True)


@pytest.mark.asyncio
async def test_resolve_backup_dir_falls_back_to_env_when_unset(db_session, monkeypatch):
    root = _make_workspace_tmp()
    try:
        monkeypatch.setenv("BACKUP_PATH", str(root / "env-backups"))
        assert await backup_service.resolve_backup_dir(db_session) == get_backup_dir()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_resolve_backup_dir_lock_overrides_stale_db_setting(db_session, monkeypatch):
    """BACKUP_PATH always wins: a DB override persisted before the lock was
    added must be ignored once BACKUP_PATH pins the directory."""
    root = _make_workspace_tmp()
    try:
        env_dir = root / "env-locked"
        monkeypatch.setenv("BACKUP_PATH", str(env_dir))
        await set_setting(db_session, "backup.directory", str(root / "stale-db-dir"))
        resolved = await backup_service.resolve_backup_dir(db_session)
        assert resolved == get_backup_dir()  # env-pinned, not the stale DB value
        assert resolved == env_dir.resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)
