"""Existing subtitle resolution (ffprobe + Emby fallback)."""
import asyncio
import json
import shutil

import pytest

from services import opensubtitles

from _subtitle_fakes import _FakeProc, _FakeResponse, _make_workspace_tmp


@pytest.mark.asyncio
async def test_get_existing_subtitles_resolves_path_from_media_categories(monkeypatch):
    root = _make_workspace_tmp()
    try:
        db = object()
        media_root = root / "local-media"
        movie_dir = media_root / "Films"
        movie_dir.mkdir(parents=True)
        movie_file = movie_dir / "movie.mkv"
        movie_file.write_bytes(b"fake-video")
        subtitle_file = movie_dir / "movie.fr.srt"
        subtitle_file.write_text("1\n00:00:01,000 --> 00:00:02,000\nBonjour\n", encoding="utf-8")

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
                            "MediaStreams": [],
                        }],
                    },
                )

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            assert cmd[-1] == str(movie_file.resolve())
            return _FakeProc(stdout=json.dumps({
                "streams": [
                    {
                        "index": 1,
                        "codec_type": "audio",
                        "codec_name": "aac",
                        "channels": 2,
                        "bit_rate": "192000",
                        "tags": {"language": "fra"},
                        "disposition": {"default": 1},
                    },
                    {
                        "index": 2,
                        "codec_type": "subtitle",
                        "codec_name": "subrip",
                        "tags": {"language": "fre", "title": "Francais"},
                        "disposition": {"default": 0, "forced": 0},
                    },
                ],
            }).encode("utf-8"))

        monkeypatch.setattr("services.emby._get_emby_config", fake_cfg)
        monkeypatch.setattr("services.media_manager.get_categories", fake_get_categories)
        monkeypatch.setattr(opensubtitles.existing, "get_internal_client", lambda: FakeClient())
        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

        result = await opensubtitles.get_existing_subtitles(db, "item-1")

        assert result["analysis_source"] == "ffprobe"
        assert result["file_path"] == str(movie_file.resolve())
        assert any(s["is_external"] for s in result["streams"])
        assert any(s["language"] == "fre" and not s["is_external"] for s in result["streams"])
        assert result["audio_streams"][0]["language"] == "fra"
        assert result["audio_streams"][0]["codec"] == "AAC"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_get_existing_subtitles_falls_back_to_emby_streams_when_ffprobe_fails(monkeypatch):
    root = _make_workspace_tmp()
    try:
        db = object()
        media_root = root / "local-media"
        movie_dir = media_root / "Films"
        movie_dir.mkdir(parents=True)
        movie_file = movie_dir / "movie.mkv"
        movie_file.write_bytes(b"fake-video")

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
                            "MediaStreams": [
                                {
                                    "Index": 1,
                                    "Type": "Audio",
                                    "Codec": "dts",
                                    "Language": "eng",
                                    "Channels": 6,
                                    "BitRate": 1500000,
                                    "IsDefault": True,
                                },
                                {
                                    "Index": 2,
                                    "Type": "Subtitle",
                                    "Codec": "subrip",
                                    "Language": "fre",
                                    "IsDefault": False,
                                    "IsForced": False,
                                    "IsExternal": False,
                                },
                            ],
                        }],
                    },
                )

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            raise FileNotFoundError("ffprobe missing")

        monkeypatch.setattr("services.emby._get_emby_config", fake_cfg)
        monkeypatch.setattr("services.media_manager.get_categories", fake_get_categories)
        monkeypatch.setattr(opensubtitles.existing, "get_internal_client", lambda: FakeClient())
        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

        result = await opensubtitles.get_existing_subtitles(db, "item-2")

        assert result["analysis_source"] == "emby"
        assert result["file_path"] == str(movie_file.resolve())
        assert result["streams"][0]["language"] == "fre"
        assert result["streams"][0]["codec"] == "SUBRIP"
        assert result["audio_streams"][0]["language"] == "eng"
        assert result["audio_streams"][0]["channels"] == 6
    finally:
        shutil.rmtree(root, ignore_errors=True)
