"""Shared setup helpers for the media-manager test suite.

Loaded by the media-manager tests that need a single category bound to a
fresh temp directory (previously each file carried its own copy).
"""
from __future__ import annotations

from pathlib import Path

from services import media_manager


def single_media_root(monkeypatch, tmp_path: Path, *, key: str = "media") -> Path:
    """Configure one media-root category bound to a fresh tmp dir, return it."""
    media_root = tmp_path / "media"
    media_root.mkdir()
    monkeypatch.setattr(
        media_manager.categories,
        "_categories_cache",
        [{"key": key, "label": "media", "path": str(media_root.resolve())}],
    )
    return media_root
