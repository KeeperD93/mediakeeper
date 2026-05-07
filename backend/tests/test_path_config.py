import shutil
import uuid
from pathlib import Path

import pytest

from services import path_config
from services.path_config import (
    get_backup_dir,
    get_configured_path_roots,
    get_existing_media_path_roots,
    is_path_within_backup_dir,
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


def test_get_backup_dir_raises_in_prod_without_env(monkeypatch):
    """When BACKUP_PATH is unset and DATA_ROOT is mounted (container case),
    the helper must refuse to fall back to /data/backups so backups never
    end up inside the same volume as the database they protect."""
    root = _make_workspace_tmp()
    try:
        data_root = root / "data"
        data_root.mkdir()
        monkeypatch.delenv("BACKUP_PATH", raising=False)
        monkeypatch.setattr(path_config, "DATA_ROOT", data_root)

        with pytest.raises(RuntimeError, match=r"BACKUP_PATH"):
            get_backup_dir()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_backup_dir_dev_fallback_when_no_data_root(monkeypatch):
    """Development fallback (no /data, no BACKUP_PATH) keeps using a backups
    directory under the project root — required for local pytest runs and
    contributors that do not mount /data."""
    root = _make_workspace_tmp()
    try:
        absent_data_root = root / "absent-data"
        # Do not create absent_data_root → DATA_ROOT.is_dir() returns False.
        monkeypatch.delenv("BACKUP_PATH", raising=False)
        monkeypatch.setattr(path_config, "DATA_ROOT", absent_data_root)

        assert get_backup_dir() == (path_config.PROJECT_ROOT / "backups").resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_is_path_within_backup_dir_recognises_dir_and_descendants(monkeypatch):
    """Backup-zone detection is the building block used by media-resolution
    helpers to refuse to traverse anything that lives in or under the backup
    directory."""
    root = _make_workspace_tmp()
    try:
        backup_dir = root / "backups"
        backup_dir.mkdir()
        (backup_dir / "nested").mkdir()
        media_dir = root / "medias"
        media_dir.mkdir()

        monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

        assert is_path_within_backup_dir(backup_dir) is True
        assert is_path_within_backup_dir(backup_dir / "nested") is True
        assert is_path_within_backup_dir(backup_dir / "nested" / "file.zip") is True
        assert is_path_within_backup_dir(media_dir) is False
        assert is_path_within_backup_dir(media_dir / "movie.mkv") is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_existing_media_path_roots_excludes_backup_zone(monkeypatch):
    """When ``MEDIAKEEPER_PATH_ROOTS`` mixes media and backup roots (or a
    descendant of the backup directory), only the genuine media surfaces are
    exposed for media-resolution helpers."""
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        backup_root = root / "backups"
        backup_root.mkdir()
        nested_in_backup = backup_root / "shard-a"
        nested_in_backup.mkdir()

        monkeypatch.setenv(
            "MEDIAKEEPER_PATH_ROOTS",
            f"{media_root};{backup_root};{nested_in_backup}",
        )
        monkeypatch.setenv("BACKUP_PATH", str(backup_root))

        media_roots = get_existing_media_path_roots()

        # Both the backup root itself and a child of the backup root are
        # filtered out; the media root is preserved.
        assert media_roots == [media_root.resolve()]
        # Sanity: ``set_backup_directory`` and other backup flows still see
        # the unfiltered list — we did not change that helper.
        from services.path_config import get_existing_path_roots

        unfiltered = set(get_existing_path_roots())
        assert backup_root.resolve() in unfiltered
        assert nested_in_backup.resolve() in unfiltered
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_existing_media_path_roots_falls_back_when_backup_dir_unknown(monkeypatch):
    """If ``get_backup_dir`` cannot resolve (production refuses without
    ``BACKUP_PATH``), the helper degrades gracefully: we cannot enforce
    exclusion, so we expose the configured media roots as-is rather than
    erroring out and breaking media surfaces."""
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
        monkeypatch.delenv("BACKUP_PATH", raising=False)
        # Simulate a mounted ``DATA_ROOT`` so ``get_backup_dir`` raises.
        data_root = root / "data"
        data_root.mkdir()
        monkeypatch.setattr(path_config, "DATA_ROOT", data_root)

        assert get_existing_media_path_roots() == [media_root.resolve()]
    finally:
        shutil.rmtree(root, ignore_errors=True)
