"""Tests for subtitle tools: external delete, fix encoding, check desync."""
import shutil
from pathlib import Path

from services import opensubtitles
from services.opensubtitles import delete_external_subtitle
from services.subtitle_tools import check_desync, fix_encoding

from _subtitle_fakes import _make_workspace_tmp


def test_delete_external_subtitle_deletes_allowed_file(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        subtitle_file = media_root / "movie.fr.srt"
        subtitle_file.write_text("1\n00:00:01,000 --> 00:00:02,000\nBonjour\n", encoding="utf-8")
        deleted_paths = []

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))
        monkeypatch.setattr(
            opensubtitles.Path,
            "unlink",
            lambda self: deleted_paths.append(str(self)),
        )

        result = delete_external_subtitle(str(subtitle_file))

        assert result["success"] is True
        assert deleted_paths == [str(subtitle_file.resolve())]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_delete_external_subtitle_rejects_non_subtitle_extension(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        text_file = media_root / "notes.txt"
        text_file.write_text("hello", encoding="utf-8")

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = delete_external_subtitle(str(text_file))

        assert result["error"] == "File type not allowed"
        assert text_file.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_fix_encoding_rejects_file_outside_configured_roots(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        outside_dir = root / "outside"
        outside_dir.mkdir()
        subtitle_file = outside_dir / "movie.fr.srt"
        subtitle_file.write_text("bonjour", encoding="utf-8")

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = fix_encoding(str(subtitle_file))

        assert result["converted"] is False
        assert result["error"] == "path_outside_configured_zones"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_fix_encoding_keeps_utf8_file_inside_allowed_root(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        subtitle_file = media_root / "movie.fr.srt"
        subtitle_file.write_text("1\n00:00:01,000 --> 00:00:02,000\nAlready UTF-8\n", encoding="utf-8")

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = fix_encoding(str(subtitle_file))

        assert result["converted"] is False
        assert Path(result["path"]) == subtitle_file.resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_check_desync_detects_large_delta_inside_allowed_root(monkeypatch):
    root = _make_workspace_tmp()
    try:
        media_root = root / "media"
        media_root.mkdir()
        subtitle_file = media_root / "movie.fr.srt"
        subtitle_file.write_text(
            "1\n00:00:10,000 --> 00:00:12,000\nBonjour\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("MEDIAKEEPER_PATH_ROOTS", str(media_root))

        result = check_desync(str(subtitle_file), media_duration_sec=1, threshold_sec=5)

        assert result["desynced"] is True
        assert result["delta_sec"] == 11.0
        assert result["srt_duration_sec"] == 12.0
    finally:
        shutil.rmtree(root, ignore_errors=True)
