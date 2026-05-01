import shutil
import uuid
from pathlib import Path

from services import path_config
from services.path_config import (
    get_backup_dir,
    get_configured_path_roots,
    is_path_within_roots,
    validate_path_in_roots,
)


def _make_workspace_tmp() -> Path:
    root = Path(__file__).resolve().parent / "_tmp_path_config" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_get_configured_path_roots_from_env(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        backups_root = root / "backups"
        media_root.mkdir()
        backups_root.mkdir()

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", f"{media_root};{backups_root}")

        roots = get_configured_path_roots()

        assert roots == [media_root.resolve(), backups_root.resolve()]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_configured_path_roots_deduplicates_and_accepts_multiple_separators(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        backups_root = root / "backups"
        media_root.mkdir()
        backups_root.mkdir()

        monkeypatch.setenv(
            "MEDIAKEEPER_PATH_ROOTS",
            f"{media_root}, {backups_root}; {media_root}",
        )

        roots = get_configured_path_roots()

        assert roots == [media_root.resolve(), backups_root.resolve()]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_validate_path_in_roots_accepts_child_and_rejects_outside(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        inside_file = media_root / "movie.fr.srt"
        inside_file.write_text("1\n00:00:01,000 --> 00:00:02,000\nBonjour\n", encoding="utf-8")

        outside_file = root / "elsewhere" / "movie.fr.srt"
        outside_file.parent.mkdir()
        outside_file.write_text("x", encoding="utf-8")

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        resolved, error = validate_path_in_roots(
            str(inside_file),
            must_be_dir=False,
            allowed_suffixes={".srt"},
            label="Subtitle file",
        )
        assert error is None
        assert resolved == inside_file.resolve()
        assert is_path_within_roots(inside_file)

        _, error = validate_path_in_roots(
            str(outside_file),
            must_be_dir=False,
            allowed_suffixes={".srt"},
            label="Subtitle file",
        )
        assert error == "path_outside_configured_zones"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_validate_path_in_roots_requires_configured_roots(monkeypatch):
    root = _make_workspace_tmp()
    try:
        file_path = root / "movie.fr.srt"
        file_path.write_text("x", encoding="utf-8")
        monkeypatch.delenv("MEDIAKEEPER_PATH_ROOTS", raising=False)

        _, error = validate_path_in_roots(
            str(file_path),
            must_be_dir=False,
            allowed_suffixes={".srt"},
            label="Subtitle file",
        )

        assert error == "no_roots_configured"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_validate_path_in_roots_requires_existing_parent_for_missing_targets(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        missing_file = media_root / "missing" / "movie.fr.srt"

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        _, error = validate_path_in_roots(
            str(missing_file),
            allow_missing=True,
            must_be_dir=False,
            allowed_suffixes={".srt"},
            label="Subtitle file",
        )

        assert error == "parent_directory_not_found"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_backup_dir_uses_env(monkeypatch):
    root = _make_workspace_tmp()
    try:
        backup_dir = root / "custom-backups"
        monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

        assert get_backup_dir() == backup_dir.resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_backup_dir_prefers_data_root_when_available(monkeypatch):
    root = _make_workspace_tmp()
    try:
        data_root = root / "data"
        data_root.mkdir()
        monkeypatch.delenv("BACKUP_PATH", raising=False)
        monkeypatch.setattr(path_config, "DATA_ROOT", data_root)

        assert get_backup_dir() == (data_root / "backups").resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)
