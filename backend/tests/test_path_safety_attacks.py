"""Path-traversal attack coverage for every central path validator.

CodeQL flags 70 ``py/path-injection`` sinks across the backend because
it cannot trace validation through helper functions. The audit
(2026-05-22) confirmed each one is in fact gated by one of:

* :func:`services.path_config.validate_path_in_roots`
* :func:`services.media_manager._paths._validate_path`
* :func:`services.logs._files._safe_log_path`
* :func:`services.portal.avatars._safe_filename` / :func:`avatar_path_for`
* :func:`core.app_spa._resolve_spa_file`
* :func:`api.media._helpers._is_allowed_browse_path`
* :func:`services.backup.get_backup_path`

This module is the explicit evidence that those validators reject the
classic attack payloads. If a future refactor weakens any of them,
this test file fails before the regression reaches production. It is
also the rationale we point at when dismissing the CodeQL alerts.
"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from api.media._helpers import _is_allowed_browse_path
from core.app_spa import _resolve_spa_file
from services import backup as backup_service
from services.logs import _files
from services.media_manager._paths import _is_allowed_path, _validate_path
from services.path_config import is_path_within_backup_dir, validate_path_in_roots
from services.portal.avatars import _safe_filename, avatar_path_for


def _make_workspace_tmp(prefix: str) -> Path:
    """Throwaway dir inside the backend workspace (sandbox-friendly)."""
    root = Path(__file__).resolve().parent / prefix / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


# validate_path_in_roots — classic path-traversal payloads


def test_validate_rejects_parent_dir_traversal(monkeypatch):
    workspace = _make_workspace_tmp("_attack_validate")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        (workspace / "secret.txt").write_text("nope", encoding="utf-8")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        attack = str(media_root / ".." / "secret.txt")
        _, error = validate_path_in_roots(
            attack, must_be_dir=False, label="Test path"
        )
        assert error == "path_outside_configured_zones"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_validate_rejects_absolute_path_outside_roots(monkeypatch):
    workspace = _make_workspace_tmp("_attack_validate")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        _, error = validate_path_in_roots(
            "/etc/passwd", must_be_dir=False, label="Test path"
        )
        assert error in {"path_outside_configured_zones", "invalid_path"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_validate_rejects_empty_path():
    _, error = validate_path_in_roots(
        "", must_be_dir=False, label="Test path"
    )
    assert error is not None


def test_validate_rejects_path_with_nul_byte(monkeypatch):
    """``\\x00`` is famously used to truncate filenames in C-level libs;
    pathlib raises ``ValueError`` before we even hit the roots check."""
    workspace = _make_workspace_tmp("_attack_validate")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        _, error = validate_path_in_roots(
            "movie.mkv\x00.txt", must_be_dir=False, label="Test path"
        )
        assert error is not None
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_validate_rejects_double_dot_inside_resolved_path(monkeypatch):
    workspace = _make_workspace_tmp("_attack_validate")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        sibling = workspace / "sibling"
        sibling.mkdir()
        (sibling / "loot.txt").write_text("x", encoding="utf-8")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        attack = f"{media_root}/sub/../../sibling/loot.txt"
        _, error = validate_path_in_roots(
            attack, must_be_dir=False, label="Test path"
        )
        assert error == "path_outside_configured_zones"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_is_path_within_backup_dir_flags_archive(monkeypatch):
    """Building block: the helper that powers the backup-zone refusal
    in ``_validate_path``. End-to-end refusal is covered by
    :func:`test_media_validate_rejects_backup_zone`."""
    workspace = _make_workspace_tmp("_attack_validate")
    try:
        media_root = workspace / "media"
        backup_dir = media_root / "backups"
        backup_dir.mkdir(parents=True)
        archive = backup_dir / "mediakeeper_backup_20260523_010203.zip"
        archive.write_text("zip", encoding="utf-8")
        outside = media_root / "movie.mkv"
        outside.write_bytes(b"\x00")
        monkeypatch.setenv("BACKUP_PATH", str(backup_dir))

        assert is_path_within_backup_dir(archive) is True
        assert is_path_within_backup_dir(outside) is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# _validate_path (media_manager) — same attacks, application layer


def test_media_validate_rejects_parent_dir_traversal(monkeypatch):
    workspace = _make_workspace_tmp("_attack_media")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
        from services.media_manager import categories as cat_mod

        monkeypatch.setattr(
            cat_mod,
            "MEDIA_FOLDERS",
            {"movies": str(media_root)},
        )

        attack = str(media_root / ".." / "secret.txt")
        assert _validate_path(attack) == "path_not_allowed"
        assert _is_allowed_path(attack) is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_media_validate_rejects_backup_zone(monkeypatch):
    workspace = _make_workspace_tmp("_attack_media")
    try:
        media_root = workspace / "media"
        backup_dir = media_root / "backups"
        backup_dir.mkdir(parents=True)
        target = backup_dir / "archive.zip"
        target.write_text("zip", encoding="utf-8")
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
        monkeypatch.setenv("BACKUP_PATH", str(backup_dir))
        from services.media_manager import categories as cat_mod

        monkeypatch.setattr(
            cat_mod,
            "MEDIA_FOLDERS",
            {"movies": str(media_root)},
        )

        assert _validate_path(str(target)) == "path_not_allowed"
        assert _is_allowed_path(str(target)) is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_media_validate_accepts_path_inside_root(monkeypatch):
    workspace = _make_workspace_tmp("_attack_media")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        legit = media_root / "movie.mkv"
        legit.write_bytes(b"\x00" * 10)
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
        from services.media_manager import categories as cat_mod

        monkeypatch.setattr(
            cat_mod,
            "MEDIA_FOLDERS",
            {"movies": str(media_root)},
        )

        assert _validate_path(str(legit)) is None
        assert _is_allowed_path(str(legit)) is True
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlink creation requires elevated privileges on Windows",
)
def test_media_validate_rejects_symlink_targeting_outside(monkeypatch):
    workspace = _make_workspace_tmp("_attack_media")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        secret = workspace / "secret.txt"
        secret.write_text("s3cret", encoding="utf-8")
        link = media_root / "shortcut.lnk"
        link.symlink_to(secret)
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
        from services.media_manager import categories as cat_mod

        monkeypatch.setattr(
            cat_mod,
            "MEDIA_FOLDERS",
            {"movies": str(media_root)},
        )

        # ``resolve()`` follows the symlink → escapes the media root.
        assert _validate_path(str(link)) == "path_not_allowed"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# _safe_log_path — regex-locked filename whitelist


@pytest.mark.parametrize(
    "attack",
    [
        "../outside.txt",
        "..\\outside.txt",
        "/etc/passwd",
        "mediakeeper.log",
        "mediakeeper",
        "",
        "evil/sub.txt",
        "a" * 121 + ".txt",
        "secret%20file.txt",
    ],
)
def test_safe_log_path_rejects_attack_payload(attack, workspace_tmp_path):
    logs_dir = workspace_tmp_path / "logs"
    logs_dir.mkdir()
    with patch("services.logs._files.LOG_DIR", logs_dir):
        assert _files._safe_log_path(attack) is None


def test_safe_log_path_accepts_simple_txt(workspace_tmp_path):
    logs_dir = workspace_tmp_path / "logs"
    logs_dir.mkdir()
    with patch("services.logs._files.LOG_DIR", logs_dir):
        assert _files._safe_log_path("mediakeeper.txt") is not None


# _safe_filename / avatar_path_for — basename-only enforcement


@pytest.mark.parametrize(
    "attack",
    [
        "",
        ".hidden.png",
        ".",
        ".png",  # leading-dot basename (rejected by the .-prefix guard)
    ],
)
def test_safe_filename_rejects_attack(attack):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _safe_filename(attack)
    assert exc.value.status_code == 400


def test_safe_filename_strips_traversal_segments():
    """``Path.name`` returns only the final segment, so traversal
    payloads collapse to a benign basename. The endpoint then runs
    :func:`avatar_path_for` which enforces containment."""
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("subdir/inner/avatar.png") == "avatar.png"


def test_avatar_path_for_keeps_target_inside_avatar_dir(workspace_tmp_path):
    avatar_dir = workspace_tmp_path / "avatars"
    avatar_dir.mkdir()
    with patch("services.portal.avatars.AVATAR_DIR", avatar_dir):
        target = avatar_path_for("alice.png")
    assert target.resolve().parent == avatar_dir.resolve()


# _resolve_spa_file — frontend asset containment


@pytest.mark.parametrize(
    "attack",
    [
        "../outside.txt",
        "../../etc/passwd",
        "subdir/../../etc/passwd",
        "/etc/passwd",
        "/absolute/asset.txt",
        ".env",
        ".htaccess",
        "subdir/.git/HEAD",
        "asset with space.txt",
        "asset;name.txt",
    ],
)
def test_resolve_spa_file_rejects_traversal(attack, workspace_tmp_path):
    root = workspace_tmp_path / "frontend-dist"
    root.mkdir()
    (root / "asset.txt").write_text("ok", encoding="utf-8")
    (workspace_tmp_path / "outside.txt").write_text("nope", encoding="utf-8")

    assert _resolve_spa_file(root, attack) is None


@pytest.mark.parametrize(
    "asset_path",
    [
        "asset.txt",
        "index-DXyZ_abc.js",
        "favicon.ico",
        "logo-x123.png",
        "subdir/nested-asset.css",
    ],
)
def test_resolve_spa_file_accepts_legit_vite_asset(asset_path, workspace_tmp_path):
    """The strict per-segment whitelist must not reject the conventional
    Vite-built asset names (hash suffix, dotted extension)."""
    root = workspace_tmp_path / "frontend-dist"
    root.mkdir()
    target = root / asset_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("ok", encoding="utf-8")

    assert _resolve_spa_file(root, asset_path) == target.resolve()


def test_resolve_spa_file_rejects_empty_path(workspace_tmp_path):
    root = workspace_tmp_path / "frontend-dist"
    root.mkdir()
    assert _resolve_spa_file(root, "") is None


def test_resolve_spa_file_rejects_nul_byte(workspace_tmp_path):
    """``\\x00`` is famously used to truncate filenames in C-level libs;
    pathlib raises ``ValueError`` on resolve, which the helper must catch."""
    root = workspace_tmp_path / "frontend-dist"
    root.mkdir()
    assert _resolve_spa_file(root, "asset\x00.txt") is None


# _is_allowed_browse_path — root containment (api/media/_helpers)


def test_is_allowed_browse_path_rejects_nul_byte(monkeypatch):
    workspace = _make_workspace_tmp("_attack_browse")
    try:
        media_root = workspace / "media"
        media_root.mkdir()
        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        assert _is_allowed_browse_path(Path("movie.mkv\x00.txt")) is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# get_backup_path — regex filename + containment


def test_backup_get_path_rejects_traversal(monkeypatch):
    workspace = _make_workspace_tmp("_attack_backup")
    try:
        backup_dir = workspace / "backups"
        backup_dir.mkdir()
        valid = backup_dir / "mediakeeper_backup_20260522_010203.zip"
        valid.write_text("zip", encoding="utf-8")
        monkeypatch.setenv("BACKUP_PATH", str(backup_dir))
        monkeypatch.setattr(backup_service._state, "_runtime_backup_dir", None)

        assert backup_service.get_backup_path(
            "../mediakeeper_backup_20260522_010203.zip"
        ) is None
        assert backup_service.get_backup_path("/etc/passwd") is None
        assert backup_service.get_backup_path("random.zip") is None
        # Sanity: the legitimate name still resolves.
        assert backup_service.get_backup_path(valid.name) == valid.resolve()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
