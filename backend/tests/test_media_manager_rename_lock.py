"""Concurrent renames to the same destination must not silently overwrite.

``apply_rename`` serialises the dest-existence check and the os-level rename
under a module lock; two renames targeting the same name therefore resolve to
exactly one success and one ``destination_exists`` instead of racing between
the check and the rename (TOCTOU) into a lost write.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from services import media_manager


def _single_media_root(monkeypatch, tmp_path: Path) -> Path:
    media_root = tmp_path / "media"
    media_root.mkdir()
    monkeypatch.setattr(
        media_manager.categories,
        "_categories_cache",
        [{"key": "media", "label": "media", "path": str(media_root.resolve())}],
    )
    return media_root


@pytest.mark.asyncio
async def test_concurrent_rename_to_same_destination_does_not_overwrite(monkeypatch, tmp_path):
    media_root = _single_media_root(monkeypatch, tmp_path)
    a = media_root / "a.mkv"
    a.write_bytes(b"AAA")
    b = media_root / "b.mkv"
    b.write_bytes(b"BBB")

    results = await asyncio.gather(
        media_manager.apply_rename(str(a), "c.mkv"),
        media_manager.apply_rename(str(b), "c.mkv"),
    )

    successes = [r for r in results if r.get("success")]
    rejections = [r for r in results if r.get("error") == "destination_exists"]
    assert len(successes) == 1, results
    assert len(rejections) == 1, results

    target = media_root / "c.mkv"
    assert target.exists()
    # The winner's bytes are intact — no corruption/truncation from a race.
    assert target.read_bytes() in (b"AAA", b"BBB")
    # The loser's source file is left in place (its rename was refused).
    assert a.exists() or b.exists()
