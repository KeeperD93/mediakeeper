"""SPA static file containment tests."""
from __future__ import annotations

from core.app_spa import _resolve_spa_file


def test_resolve_spa_file_accepts_file_inside_root(tmp_path):
    root = tmp_path / "frontend-dist"
    root.mkdir()
    asset = root / "asset.txt"
    asset.write_text("ok", encoding="utf-8")

    assert _resolve_spa_file(root, "asset.txt") == asset.resolve()


def test_resolve_spa_file_rejects_prefix_sibling_escape(tmp_path):
    root = tmp_path / "frontend-dist"
    root.mkdir()
    sibling = tmp_path / "frontend-dist-evil"
    sibling.mkdir()
    (sibling / "asset.txt").write_text("nope", encoding="utf-8")

    assert _resolve_spa_file(root, "../frontend-dist-evil/asset.txt") is None
