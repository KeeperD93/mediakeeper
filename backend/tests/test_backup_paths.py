import shutil
import uuid
from pathlib import Path

import pytest

from services import backup as backup_service


def _make_workspace_tmp() -> Path:
    root = Path(__file__).resolve().parent / "_tmp_backup_paths" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_set_backup_directory_rejects_when_locked_by_compose(monkeypatch):
    root = _make_workspace_tmp()
    try:
        compose_backup_dir = root / "compose-backups"
        monkeypatch.setenv("BACKUP_PATH", str(compose_backup_dir))
        monkeypatch.setattr(backup_service._state, "_runtime_backup_dir", None)

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
        monkeypatch.setattr(backup_service._state, "_runtime_backup_dir", None)

        backup_service.set_backup_directory(str(target))

        assert target.exists()
        assert target.is_dir()
        assert backup_service.get_current_backup_dir() == target.resolve()
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
        monkeypatch.setattr(backup_service._state, "_runtime_backup_dir", None)

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
        monkeypatch.setattr(backup_service._state, "_runtime_backup_dir", None)

        directories = backup_service.list_available_backup_dirs()

        assert str(mounted_root.resolve()) in directories
        assert str(configured_backup_dir.resolve()) in directories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_backup_path_rejects_non_backup_zip_names(monkeypatch):
    root = _make_workspace_tmp()
    try:
        backup_dir = root / "backups"
        backup_dir.mkdir()
        (backup_dir / "manual.zip").write_text("not a backup", encoding="utf-8")
        valid = backup_dir / "mediakeeper_backup_20260429_010203.zip"
        valid.write_text("backup", encoding="utf-8")

        monkeypatch.setenv("BACKUP_PATH", str(backup_dir))
        monkeypatch.setattr(backup_service._state, "_runtime_backup_dir", None)

        assert backup_service.get_backup_path("manual.zip") is None
        assert backup_service.get_backup_path("../mediakeeper_backup_20260429_010203.zip") is None
        assert backup_service.get_backup_path(valid.name) == valid.resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)
