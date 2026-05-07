"""Safe FFmpeg remux flow: remove_stream / remove_streams_batch.

Source file must never be deleted, overwritten or moved if backup, FFmpeg or
ffprobe fails. FFmpeg and ffprobe are mocked — no real binaries are spawned.
"""
import asyncio
import shutil
import time
from pathlib import Path

import pytest

from services import opensubtitles
from services.opensubtitles import _remux as remux_mod
from services.opensubtitles import remove as remove_mod
from services.opensubtitles import rollback_retention

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


@pytest.mark.asyncio
async def test_remove_stream_aborts_on_insufficient_disk_space(monkeypatch):
    """Disk-space guard refuses the remux before copying or invoking FFmpeg.

    The source must stay byte-for-byte identical, no rollback artifact is
    created, no subprocess is spawned, and the API response must use the
    short ``insufficient_disk_space`` code without leaking any filesystem
    path.
    """
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

        copy_calls: list[tuple] = []
        real_copy2 = shutil.copy2

        def _track_copy(src, dst, *args, **kwargs):
            copy_calls.append((src, dst))
            return real_copy2(src, dst, *args, **kwargs)

        monkeypatch.setattr(shutil, "copy2", _track_copy)

        class _Usage:
            def __init__(self, free: int):
                self.total = free + 1
                self.used = 1
                self.free = free

        # Free space far below required (source bytes * 2 + margin).
        monkeypatch.setattr(remux_mod.shutil, "disk_usage", lambda _path: _Usage(free=128))

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result == {"error": "insufficient_disk_space"}
        # Response must not contain any filesystem path.
        for value in result.values():
            if isinstance(value, str):
                assert str(movie_dir) not in value
                assert "/" not in value or value == "insufficient_disk_space"
        # No subprocess, no rollback copy: the guard fires before any I/O.
        assert state.commands == []
        assert copy_calls == []
        assert movie_file.read_bytes() == b"original-bytes"
        assert _list_tmp_leftovers(movie_dir, "movie") == []
        assert _list_rollback_artifacts(movie_dir, "movie") == []
        assert state.refresh_calls == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_proceeds_when_disk_space_is_sufficient(monkeypatch):
    """The disk-space guard is non-blocking when free space exceeds the
    estimated requirement (source size * 2 + margin)."""
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, _movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        class _Usage:
            def __init__(self, free: int):
                self.total = free + 1
                self.used = 1
                self.free = free

        # Plenty of free space (1 GiB) — guard must pass through.
        monkeypatch.setattr(remux_mod.shutil, "disk_usage", lambda _path: _Usage(free=1 << 30))

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result["success"] is True
        assert result["rollback_kept"] is True
        assert movie_file.read_bytes() == b"fake-remuxed-bytes"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remove_stream_purges_old_rollbacks_after_success(monkeypatch):
    """Successful remux opportunistically purges aged rollback siblings.

    A 60-day-old rollback in the same directory must be removed; a fresh
    rollback (the one just produced by the current remux) must be kept; an
    unrelated dotfile that happens to look similar must never be touched.
    """
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        # Stale rollback artifact, older than the default 30-day retention.
        stale = movie_dir / ".other.rollback-aaaaaaaaaaaa.mkv"
        stale.write_bytes(b"stale-rollback")
        old_mtime = time.time() - 60 * 24 * 3600
        import os as _os
        _os.utime(str(stale), (old_mtime, old_mtime))

        # Lookalike but not a strict rollback artifact (token too short).
        lookalike = movie_dir / ".note.rollback-short.txt"
        lookalike.write_bytes(b"unrelated")

        # Sibling media file — must never be considered.
        sibling = movie_dir / "other.mkv"
        sibling.write_bytes(b"other-media")

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result["success"] is True
        # Stale rollback removed, lookalike + sibling untouched.
        assert not stale.exists()
        assert lookalike.exists()
        assert sibling.exists() and sibling.read_bytes() == b"other-media"
        # The freshly-created rollback for the current operation is kept.
        rollbacks = _list_rollback_artifacts(movie_dir, "movie")
        assert len(rollbacks) == 1
        assert rollbacks[0].read_bytes() == b"original-bytes"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_purge_rollback_artifacts_removes_only_aged_strict_matches(tmp_path: Path):
    """Direct unit test of the retention helper — no remux flow involved."""
    fresh = tmp_path / ".movie.rollback-1234567890ab.mkv"
    fresh.write_bytes(b"fresh")
    aged = tmp_path / ".movie.rollback-cafebabecafe.mkv"
    aged.write_bytes(b"aged")
    aged_mtime = time.time() - 90 * 24 * 3600
    import os as _os
    _os.utime(str(aged), (aged_mtime, aged_mtime))

    # Files that must NEVER be deleted by the helper:
    media = tmp_path / "movie.mkv"
    media.write_bytes(b"media")
    bad_token = tmp_path / ".movie.rollback-not-hex-here.mkv"
    bad_token.write_bytes(b"bad")
    backup_zip = tmp_path / "mediakeeper_backup_20260101_010101.zip"
    backup_zip.write_bytes(b"app-backup")

    removed = rollback_retention.purge_rollback_artifacts(tmp_path)

    assert removed == 1
    assert not aged.exists()
    assert fresh.exists()
    assert media.exists()
    assert bad_token.exists()
    assert backup_zip.exists()


def test_purge_rollback_artifacts_swallows_oserror(monkeypatch, tmp_path: Path):
    """Helper must never raise: an iterdir / unlink failure stays internal."""
    target = tmp_path / ".movie.rollback-aaaaaaaaaaaa.mkv"
    target.write_bytes(b"x")
    aged_mtime = time.time() - 90 * 24 * 3600
    import os as _os
    _os.utime(str(target), (aged_mtime, aged_mtime))

    real_unlink = Path.unlink

    def _boom(self, *args, **kwargs):
        if self == target:
            raise OSError("simulated permission denied")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _boom)

    # No exception bubbles up; the file remains because unlink failed.
    removed = rollback_retention.purge_rollback_artifacts(tmp_path)
    assert removed == 0
    assert target.exists()


@pytest.mark.asyncio
async def test_remux_rollback_mtime_anchored_to_creation_not_source(monkeypatch):
    """A successful remux of a media file whose mtime is 90 days old must NOT
    produce a rollback that the opportunistic retention sweep then deletes.

    ``shutil.copy2`` preserves the source mtime, so without an explicit touch
    the freshly-created rollback inherits a 90-day-old mtime and gets purged
    immediately by the post-success retention call. The fix refreshes the
    rollback's atime/mtime to "now" right after the copy.

    The same flow must still purge an unrelated rollback that was genuinely
    aged (preexisting in the same directory, mtime older than retention).
    """
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        # Backdate the source mtime: simulates a media file that has not been
        # touched for three months. ``shutil.copy2`` will copy this mtime to
        # the rollback unless the production code refreshes it.
        ninety_days_ago = time.time() - 90 * 24 * 3600
        import os as _os
        _os.utime(str(movie_file), (ninety_days_ago, ninety_days_ago))

        # A *separate*, genuinely aged rollback already in the same directory:
        # this one must still be purged by the post-success retention sweep.
        preexisting_old = movie_dir / ".vintage.rollback-deadbeefdead.mkv"
        preexisting_old.write_bytes(b"vintage-rollback")
        _os.utime(str(preexisting_old), (ninety_days_ago, ninety_days_ago))

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result["success"] is True
        assert result["rollback_kept"] is True
        # API response must NOT leak any filesystem path for the rollback.
        for value in result.values():
            if isinstance(value, str):
                assert "rollback-" not in value
                assert str(movie_dir) not in value

        # The genuinely-old preexisting rollback was purged by the
        # opportunistic post-success sweep.
        assert not preexisting_old.exists()

        # The freshly-produced rollback is still on disk: the mtime refresh
        # made it look "born now" to the retention helper.
        rollbacks = _list_rollback_artifacts(movie_dir, "movie")
        assert len(rollbacks) == 1
        rollback = rollbacks[0]
        assert rollback.read_bytes() == b"original-bytes"
        # Sanity: the rollback's mtime is anchored to "now", not to the
        # 90-day-old source mtime. Allow a generous 5-minute window for
        # CI clock skew / slow runners.
        now = time.time()
        rollback_mtime = rollback.stat().st_mtime
        assert rollback_mtime > ninety_days_ago + 24 * 3600, (
            f"rollback mtime {rollback_mtime} is suspiciously close to the "
            f"backdated source mtime {ninety_days_ago}; the production code "
            "likely forgot to refresh it after shutil.copy2."
        )
        assert abs(now - rollback_mtime) < 300

        # Source has been replaced atomically with the remuxed bytes.
        assert movie_file.read_bytes() == b"fake-remuxed-bytes"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_remux_rollback_survives_purge_when_utime_fails(monkeypatch):
    """The current remux's rollback must survive the post-success retention
    sweep even when the ``os.utime`` mtime refresh fails.

    Without the explicit ``exclude_paths`` contract, a 90-day-old source would
    yield a rollback whose mtime ``shutil.copy2`` copied as-is, and the very
    next ``purge_rollback_artifacts`` call (made by the same remux flow)
    would delete it before any operator could use it. The fix makes the
    purge accept an exclusion set, and the remux flow always passes the
    rollback it just produced — so the safety net does not depend on
    ``os.utime`` succeeding.
    """
    root = _make_workspace_tmp()
    try:
        state = _RemuxState()
        media_streams = [
            {"Index": 0, "Type": "Video"},
            {"Index": 1, "Type": "Audio", "Language": "eng", "IsExternal": False},
        ]
        movie_file, movie_dir, payload = _setup_env(monkeypatch, root, media_streams)

        # Backdate the source mtime so that ``shutil.copy2`` produces a
        # rollback with a 90-day-old mtime when the mtime refresh fails.
        ninety_days_ago = time.time() - 90 * 24 * 3600
        import os as _os
        _os.utime(str(movie_file), (ninety_days_ago, ninety_days_ago))

        # Genuinely-aged rollback already in the directory: must still be
        # purged by the post-success sweep (regression anchor).
        preexisting_old = movie_dir / ".vintage.rollback-deadbeefdead.mkv"
        preexisting_old.write_bytes(b"vintage-rollback")
        _os.utime(str(preexisting_old), (ninety_days_ago, ninety_days_ago))

        client = _make_fake_client(state, payload)
        monkeypatch.setattr(remove_mod, "get_internal_client", lambda: client)
        _install_subprocess_fakes(monkeypatch, state)

        # Force the explicit rollback mtime refresh to fail ONLY for the
        # current rollback path. Do this at the ``asyncio.to_thread`` boundary
        # instead of monkeypatching ``os.utime`` globally: ``shutil.copy2``
        # internally calls ``os.utime`` on Linux/Python 3.12, and that copy
        # step must remain real for this test to exercise the intended fallback.
        real_to_thread = remux_mod.asyncio.to_thread

        async def _to_thread_with_utime_failure(func, *args, **kwargs):
            if func is remux_mod.os.utime and args:
                path = args[0]
            else:
                return await real_to_thread(func, *args, **kwargs)
            try:
                name = Path(path).name
            except Exception:  # noqa: BLE001 -- defensive
                name = ""
            # The current rollback file lives under movie_dir and matches
            # the strict rollback naming for our stem.
            if (
                name.startswith(".movie.rollback-")
                and Path(path).parent.resolve(strict=False)
                == movie_dir.resolve(strict=False)
            ):
                raise OSError("simulated utime failure")
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(remux_mod.asyncio, "to_thread", _to_thread_with_utime_failure)

        result = await opensubtitles.remove_stream(object(), "item-1", 1)

        assert result["success"] is True
        assert result["rollback_kept"] is True
        # API must not leak any filesystem path for the rollback.
        for value in result.values():
            if isinstance(value, str):
                assert "rollback-" not in value
                assert str(movie_dir) not in value

        # The freshly-produced rollback survived the opportunistic purge
        # despite ``os.utime`` failing — proof that the exclusion contract
        # is what protects it, not the mtime refresh.
        rollbacks = _list_rollback_artifacts(movie_dir, "movie")
        assert len(rollbacks) == 1
        rollback = rollbacks[0]
        assert rollback.read_bytes() == b"original-bytes"
        # Sanity: because the touch failed, the rollback's mtime is still
        # the 90-day-old source mtime (not refreshed). The exclusion is
        # what kept it on disk.
        rollback_mtime = rollback.stat().st_mtime
        assert abs(rollback_mtime - ninety_days_ago) < 5

        # The genuinely-aged preexisting rollback was still purged: the
        # exclusion only protects the rollback we just produced, not the
        # entire directory.
        assert not preexisting_old.exists()

        # Source replaced atomically with the remuxed bytes.
        assert movie_file.read_bytes() == b"fake-remuxed-bytes"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_purge_rollback_artifacts_honours_exclude_paths(tmp_path: Path):
    """Direct unit test of the new ``exclude_paths`` contract: an aged
    rollback that would normally be purged stays on disk when its path is
    listed in the exclusion set, while peer aged rollbacks are still cleaned
    up. Comparison must be done on resolved paths so callers can pass any
    equivalent form (relative, with ``.`` segments, etc.)."""
    aged = tmp_path / ".movie.rollback-1234567890ab.mkv"
    aged.write_bytes(b"aged")
    aged_excluded = tmp_path / ".movie.rollback-cafebabecafe.mkv"
    aged_excluded.write_bytes(b"protected")
    aged_mtime = time.time() - 90 * 24 * 3600
    import os as _os
    _os.utime(str(aged), (aged_mtime, aged_mtime))
    _os.utime(str(aged_excluded), (aged_mtime, aged_mtime))

    # Pass the exclusion in a non-canonical form (extra ``.`` segment) to
    # verify the helper compares resolved paths, not raw strings.
    weird_form = tmp_path / "." / aged_excluded.name

    removed = rollback_retention.purge_rollback_artifacts(
        tmp_path,
        exclude_paths={weird_form},
    )

    assert removed == 1
    assert not aged.exists()
    assert aged_excluded.exists()
    assert aged_excluded.read_bytes() == b"protected"
