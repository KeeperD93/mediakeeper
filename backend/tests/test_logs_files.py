"""Log file path validation tests."""
from __future__ import annotations

from unittest.mock import patch

from services.logs import _files


def test_read_log_file_rejects_path_traversal(workspace_tmp_path):
    logs_dir = workspace_tmp_path / "logs"
    logs_dir.mkdir()
    outside = workspace_tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    with patch("services.logs._files.LOG_DIR", logs_dir):
        result = _files.read_log_file("../outside.txt")

    assert result["error"] == "invalid_filename"


def test_get_log_filepath_accepts_simple_txt_name(workspace_tmp_path):
    logs_dir = workspace_tmp_path / "logs"
    logs_dir.mkdir()
    log_file = logs_dir / "mediakeeper.txt"
    log_file.write_text("ok", encoding="utf-8")

    with patch("services.logs._files.LOG_DIR", logs_dir):
        assert _files.get_log_filepath("mediakeeper.txt") == log_file.resolve()


def test_get_log_filepath_rejects_non_txt_name(workspace_tmp_path):
    logs_dir = workspace_tmp_path / "logs"
    logs_dir.mkdir()
    log_file = logs_dir / "mediakeeper.log"
    log_file.write_text("nope", encoding="utf-8")

    with patch("services.logs._files.LOG_DIR", logs_dir):
        assert _files.get_log_filepath("mediakeeper.log") is None
