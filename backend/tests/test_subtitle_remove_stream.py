"""remove_stream: verify it uses the local path resolved via media_manager."""
import asyncio
import shutil

import pytest

from services import opensubtitles

from _subtitle_fakes import _FakeProc, _FakeResponse, _make_workspace_tmp


@pytest.mark.asyncio
async def test_remove_stream_uses_resolved_local_path(monkeypatch):
    root = _make_workspace_tmp()
    try:
        db = object()
        media_root = root / "local-media"
        movie_dir = media_root / "Films"
        movie_dir.mkdir(parents=True)
        movie_file = movie_dir / "movie.mkv"
        movie_file.write_bytes(b"fake-video")

        recorded_cmd = []
        moved_paths = []

        monkeypatch.delenv("MEDIAKEEPER_PATH_ROOTS", raising=False)

        async def fake_cfg(_db):
            return ("http://emby.test", "token")

        async def fake_get_categories(_db):
            return [{"key": "films", "label": "Films", "path": str(media_root)}]

        class FakeClient:
            async def get(self, url, params=None, headers=None, timeout=None):
                return _FakeResponse(
                    200,
                    {
                        "MediaSources": [{
                            "Path": "/volume1/medias/Films/movie.mkv",
                            "MediaStreams": [{
                                "Index": 1,
                                "Type": "Audio",
                                "Language": "eng",
                                "IsExternal": False,
                            }],
                        }],
                    },
                )

            async def post(self, url, headers=None, timeout=None):
                return _FakeResponse(204, {})

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            recorded_cmd.append(cmd)
            return _FakeProc()

        monkeypatch.setattr("services.emby._get_emby_config", fake_cfg)
        monkeypatch.setattr("services.media_manager.get_categories", fake_get_categories)
        monkeypatch.setattr(opensubtitles.remove, "get_internal_client", lambda: FakeClient())
        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
        monkeypatch.setattr(shutil, "move", lambda src, dst: moved_paths.append((src, dst)))

        result = await opensubtitles.remove_stream(db, "item-3", 1)

        assert result["success"] is True
        assert recorded_cmd
        assert recorded_cmd[0][2] == str(movie_file.resolve())
        assert moved_paths[-1][1] == str(movie_file.resolve())
    finally:
        shutil.rmtree(root, ignore_errors=True)
