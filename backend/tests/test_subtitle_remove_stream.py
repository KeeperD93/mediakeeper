"""Safe FFmpeg remux flow: remove_stream / remove_streams_batch.

Source file must never be deleted, overwritten or moved if backup, FFmpeg or
ffprobe fails. FFmpeg and ffprobe are mocked — no real binaries are spawned.
"""
import asyncio
import shutil

import pytest

from services import opensubtitles
from services.opensubtitles import remove as remove_mod

from _subtitle_fakes import _FakeProc, _FakeResponse, _make_workspace_tmp


class _TrackingFakeProc(_FakeProc):
    """FakeProc with kill()/wait() instrumentation for timeout tests."""

    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        super().__init__(stdout=stdout, stderr=stderr, returncode=returncode)
        self.kill_called: bool = False
        self.wait_called: bool = False

    def kill(self) -> None:
        self.kill_called = True

    async def wait(self) -> int:
        self.wait_called = True
        return self.returncode


class _RemuxState:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.ffmpeg_rc: int = 0
        self.ffmpeg_stderr: bytes = b""
        self.ffmpeg_writes_output: bool = True
        self.ffmpeg_raises_timeout: bool = False
        self.ffmpeg_timeout_consumed: bool = False
        self.ffprobe_rc: int = 0
        self.ffprobe_stderr: bytes = b""
        self.ffprobe_raises_timeout: bool = False
        self.ffprobe_timeout_consumed: bool = False
        self.refresh_calls: list[str] = []
        self.last_ffmpeg_proc: _TrackingFakeProc | None = None
        self.last_ffprobe_proc: _TrackingFakeProc | None = None


def _install_subprocess_fakes(monkeypatch, state: _RemuxState) -> None:
    async def fake_create_subprocess_exec(*cmd, **kwargs):
        state.commands.append(list(cmd))
        binary = cmd[0]
        if binary == "ffmpeg":
            output = cmd[-1]
            if state.ffmpeg_writes_output and not state.ffmpeg_raises_timeout:
                from pathlib import Path as _P
                _P(output).write_bytes(b"fake-remuxed-bytes")
            proc = _TrackingFakeProc(stderr=state.ffmpeg_stderr, returncode=state.ffmpeg_rc)
            state.last_ffmpeg_proc = proc
            return proc
        if binary == "ffprobe":
            proc = _TrackingFakeProc(stderr=state.ffprobe_stderr, returncode=state.ffprobe_rc)
            state.last_ffprobe_proc = proc
            return proc
        return _TrackingFakeProc()

    real_wait_for = asyncio.wait_for

    async def fake_wait_for(coro, timeout):
        # Only fire timeout once per binary so the recovery wait_for
        # (proc.wait() after proc.kill()) can complete normally.
        latest = state.commands[-1][0] if state.commands else ""
        should_timeout = False
        if (
            state.ffmpeg_raises_timeout
            and latest == "ffmpeg"
            and not state.ffmpeg_timeout_consumed
        ):
            should_timeout = True
            state.ffmpeg_timeout_consumed = True
        elif (
            state.ffprobe_raises_timeout
            and latest == "ffprobe"
            and not state.ffprobe_timeout_consumed
        ):
            should_timeout = True
            state.ffprobe_timeout_consumed = True

        if should_timeout:
            try:
                coro.close()
            except Exception:  # noqa: BLE001 -- best-effort cleanup of unconsumed coro
                pass
            raise asyncio.TimeoutError()
        return await real_wait_for(coro, timeout)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)


def _make_fake_client(state: _RemuxState, item_payload: dict):
    class FakeClient:
        async def get(self, url, params=None, headers=None, timeout=None):
            return _FakeResponse(200, item_payload)

        async def post(self, url, headers=None, timeout=None):
            state.refresh_calls.append(url)
            return _FakeResponse(204, {})

    return FakeClient()


def _setup_env(monkeypatch, root, media_streams):
    """Common setup: workspace + emby config + media categories + payload."""
    media_root = root / "local-media"
    movie_dir = media_root / "Films"
    movie_dir.mkdir(parents=True)
    movie_file = movie_dir / "movie.mkv"
    movie_file.write_bytes(b"original-bytes")

    monkeypatch.delenv("MEDIAKEEPER_PATH_ROOTS", raising=False)

    async def fake_cfg(_db):
        return ("http://emby.test", "token")

    async def fake_get_categories(_db):
        return [{"key": "films", "label": "Films", "path": str(media_root)}]

    monkeypatch.setattr("services.emby._get_emby_config", fake_cfg)
    monkeypatch.setattr("services.media_manager.get_categories", fake_get_categories)

    payload = {
        "MediaSources": [{
            "Path": "/media/Films/movie.mkv",
            "MediaStreams": media_streams,
        }],
    }
    return movie_file, movie_dir, payload


def _list_tmp_leftovers(movie_dir, stem: str) -> list:
    return [c for c in movie_dir.iterdir() if c.name.startswith(f".{stem}.remux-")]


def _list_rollback_artifacts(movie_dir, stem: str) -> list:
    return [c for c in movie_dir.iterdir() if c.name.startswith(f".{stem}.rollback-")]


@pytest.mark.asyncio
async def test_remove_stream_success_safe_flow(monkeypatch):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result == {
            "success": True,
            "removed_stream": 1,
            "stream_type": "audio",
            "language": "eng",
            "rollback_kept": True,
        }
        # API response must NOT leak a filesystem path for the rollback.
        for value in result.values():
            if isinstance(value, str):
                assert "rollback-" not in value
                assert str(movie_dir) not in value
        # Two subprocesses: ffmpeg then ffprobe
        binaries = [c[0] for c in state.commands]
        assert binaries == ["ffmpeg", "ffprobe"]
        ffmpeg_cmd = state.commands[0]
        assert "-map" in ffmpeg_cmd and "-0:1" in ffmpeg_cmd
        assert ffmpeg_cmd[2] == str(movie_file.resolve())
        # Source replaced atomically with tmp content
        assert movie_file.read_bytes() == b"fake-remuxed-bytes"
        # tmp cleaned up
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        # Rollback artifact kept on disk with the ORIGINAL bytes
        rollbacks = _list_rollback_artifacts(movie_dir, "movie")
        assert len(rollbacks) == 1
        assert rollbacks[0].read_bytes() == b"original-bytes"
        # Emby refresh fired exactly once after success
        assert len(state.refresh_calls) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_streams_batch_success_safe_flow(monkeypatch):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
            {"Index": 2, "Type": "Audio", "Language": "fre", "IsExternal": False},
            {"Index": 3, "Type": "Subtitle", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_streams_batch(object(), "item-2", [1, 3])

        assert result == {
            "success": True,
            "removed_count": 2,
            "removed_streams": [1, 3],
            "rollback_kept": True,
        }
        # API response must NOT leak a filesystem path for the rollback.
        for value in result.values():
            if isinstance(value, str):
                assert "rollback-" not in value
                assert str(movie_dir) not in value
        binaries = [c[0] for c in state.commands]
        assert binaries == ["ffmpeg", "ffprobe"]
        ffmpeg_cmd = state.commands[0]
        # Both indices mapped out of the output
        assert "-0:1" in ffmpeg_cmd
        assert "-0:3" in ffmpeg_cmd
        assert movie_file.read_bytes() == b"fake-remuxed-bytes"
        # tmp cleaned up; rollback kept with original bytes
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        rollbacks = _list_rollback_artifacts(movie_dir, "movie")
        assert len(rollbacks) == 1
        assert rollbacks[0].read_bytes() == b"original-bytes"
        assert len(state.refresh_calls) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_ffmpeg_failure_keeps_source(monkeypatch):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        state.ffmpeg_rc = 1
        state.ffmpeg_writes_output = False
        state.ffmpeg_stderr = b"Conversion failed: codec error\nat line 42"
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert "error" in result
        assert result["error"].startswith("ffmpeg_failed")
        # ffprobe must NOT have been called
        binaries = [c[0] for c in state.commands]
        assert binaries == ["ffmpeg"]
        # Source unchanged
        assert movie_file.read_bytes() == b"original-bytes"
        # Source untouched: no leftover tmp AND no rollback artifact kept.
        # Keeping a rollback when the source was never replaced would only
        # waste disk and confuse operators.
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        assert _list_rollback_artifacts(movie_dir, "movie") == []
        # Refresh must NOT be called on failure
        assert state.refresh_calls == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_ffprobe_failure_keeps_source(monkeypatch):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        state.ffprobe_rc = 1
        state.ffprobe_stderr = b"Invalid data found when processing input"
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result == {"error": "ffprobe_failed"}
        binaries = [c[0] for c in state.commands]
        assert binaries == ["ffmpeg", "ffprobe"]
        # Source unchanged: no atomic replace happened
        assert movie_file.read_bytes() == b"original-bytes"
        # Source untouched: no tmp leftover, no rollback artifact kept.
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        assert _list_rollback_artifacts(movie_dir, "movie") == []
        # Refresh NOT called
        assert state.refresh_calls == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_backup_failure_aborts_before_ffmpeg(monkeypatch):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        def _raise_copy(src, dst, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(shutil, "copy2", _raise_copy)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result == {"error": "backup_failed"}
        # FFmpeg / ffprobe must NOT have been spawned
        assert state.commands == []
        # Source untouched, no tmp and no rollback artifact left behind.
        assert movie_file.read_bytes() == b"original-bytes"
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        assert _list_rollback_artifacts(movie_dir, "movie") == []
        assert state.refresh_calls == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_ffmpeg_timeout_keeps_source(monkeypatch):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        state.ffmpeg_raises_timeout = True
        state.ffmpeg_writes_output = False
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result == {"error": "ffmpeg_timeout"}
        # ffprobe never reached
        binaries = [c[0] for c in state.commands]
        assert binaries == ["ffmpeg"]
        # The timed-out FFmpeg process must have been killed and reaped.
        assert state.last_ffmpeg_proc is not None
        assert state.last_ffmpeg_proc.kill_called is True
        assert state.last_ffmpeg_proc.wait_called is True
        # Source unchanged
        assert movie_file.read_bytes() == b"original-bytes"
        # No tmp leftover and no rollback kept (source was never replaced).
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        assert _list_rollback_artifacts(movie_dir, "movie") == []
        assert state.refresh_calls == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_ffprobe_timeout_keeps_source(monkeypatch):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        state.ffprobe_raises_timeout = True
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result == {"error": "ffprobe_timeout"}
        binaries = [c[0] for c in state.commands]
        assert binaries == ["ffmpeg", "ffprobe"]
        # ffprobe killed + waited; ffmpeg completed normally so no kill on it.
        assert state.last_ffprobe_proc is not None
        assert state.last_ffprobe_proc.kill_called is True
        assert state.last_ffprobe_proc.wait_called is True
        assert state.last_ffmpeg_proc is not None
        assert state.last_ffmpeg_proc.kill_called is False
        # Source unchanged: os.replace must NOT have run.
        assert movie_file.read_bytes() == b"original-bytes"
        # tmp cleaned and no rollback kept on failure path.
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        assert _list_rollback_artifacts(movie_dir, "movie") == []
        # Refresh NOT called
        assert state.refresh_calls == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_short_error_response_full_stderr_in_logs(monkeypatch, caplog):
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        state.ffmpeg_rc = 1
        state.ffmpeg_writes_output = False
        # Long, multi-line stderr — must be fully logged but only summarised in API response.
        long_stderr = (
            b"frame=  100 fps= 0 q=-1.0 size=N/A time=00:00:00.00 bitrate=N/A speed=N/A\n"
            b"frame=  200 fps= 0 q=-1.0 size=N/A time=00:00:00.00 bitrate=N/A speed=N/A\n"
            b"[matroska @ 0x1] Conversion failed: Invalid argument while remuxing stream 1\n"
            b"signature: deadbeef-cafef00d-1234567890abcdef\n"
        ) * 8
        state.ffmpeg_stderr = long_stderr
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, _movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        with caplog.at_level("ERROR", logger="mediakeeper.opensubtitles"):
            result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert "error" in result
        assert result["error"].startswith("ffmpeg_failed")
        # API response stays compact
        assert len(result["error"]) <= 160
        # But the full stderr is preserved in the logs for diagnostic
        joined_logs = "\n".join(rec.getMessage() for rec in caplog.records)
        assert "Conversion failed" in joined_logs
        # The tail (last entries) of the long stderr must be in the logs
        assert "signature: deadbeef-cafef00d-1234567890abcdef" in joined_logs
        # Source unchanged
        assert movie_file.read_bytes() == b"original-bytes"
    finally:
        shutil.rmtree(root, ignore_errors=True)
