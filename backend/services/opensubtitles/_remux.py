"""Internal remux machinery: subprocess plumbing + safe atomic remux.

Kept private (leading underscore) and separated from the public orchestration
layer in :mod:`services.opensubtitles.remove` so each module stays small and
each concern is testable in isolation:

* low-level subprocess wrappers (``_run_subprocess``, ``_cleanup_path``) ;
* pre-flight disk-space guard (``_check_remux_disk_space``) ;
* the atomic remux flow (``_safe_remux``) that owns rollback creation, FFmpeg
  invocation, ffprobe validation and atomic replacement.
"""
import asyncio
import os
import shutil
import uuid
from pathlib import Path

from ._constants import logger
from .rollback_retention import purge_rollback_artifacts

_FFMPEG_TIMEOUT_S = 300
_FFPROBE_TIMEOUT_S = 30
# Free space margin requested on top of "source size * 2" before starting
# a remux. The factor 2 covers the rollback copy + the FFmpeg tmp output
# living alongside the source on the same filesystem; the margin absorbs
# small container overhead and FFmpeg muxer growth.
_REMUX_DISK_MARGIN_BYTES = 64 * 1024 * 1024


async def _run_subprocess(cmd: list[str], timeout: int) -> tuple[int, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        # Always reap the child: a timed-out FFmpeg/ffprobe must not survive
        # the call. We kill, then wait (best-effort guarded) before re-raising.
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        except Exception as exc:  # noqa: BLE001 -- best-effort, never mask the timeout
            logger.debug(f"[opensubtitles] proc.kill() failed for {cmd[0]}: {exc}")
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
            logger.debug(f"[opensubtitles] proc.wait() after kill failed for {cmd[0]}: {exc}")
        raise

    rc = proc.returncode
    if rc is None:
        # communicate() returned without setting returncode: treat as failure
        # rather than a silent success.
        return 1, stderr or b""
    return rc, stderr or b""


def _cleanup_path(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001 -- best-effort cleanup, never block the caller
        logger.debug(f"[opensubtitles] Cleanup failed for {path}: {exc}")


def _short_stderr_tail(stderr: bytes, length: int = 100) -> str:
    return stderr.decode(errors="replace")[-length:].replace("\n", " ").strip()


def _check_remux_disk_space(source: Path) -> str | None:
    """Refuse the remux up-front if the filesystem clearly cannot host the
    rollback copy + the FFmpeg tmp output beside the source.

    Returns ``None`` when there is enough free space (or when the check itself
    cannot run, in which case we fall back to letting FFmpeg fail loudly later
    rather than block a legitimate operation on an unusual filesystem).
    Returns the short error code ``insufficient_disk_space`` when free space is
    measured and known to be too low.
    """
    try:
        size = source.stat().st_size
        usage = shutil.disk_usage(str(source.parent))
    except OSError as exc:
        logger.debug(
            f"[opensubtitles] Disk usage check skipped for {source.parent}: {exc}"
        )
        return None
    required = size * 2 + _REMUX_DISK_MARGIN_BYTES
    if usage.free < required:
        logger.error(
            "[opensubtitles] Insufficient disk space for remux: "
            f"free={usage.free} required={required} source_size={size}"
        )
        return "insufficient_disk_space"
    return None


async def _safe_remux(
    source: Path,
    drop_indices: list[int],
) -> tuple[str | None, Path | None]:
    """Remux *source* dropping *drop_indices*, validating with ffprobe before atomic replace.

    Steps:
      1. Pre-create a sibling rollback copy of *source* before invoking FFmpeg.
      2. Run FFmpeg into a sibling tmp file (same dir → same filesystem).
      3. Validate the tmp file with ffprobe.
      4. Atomically replace *source* via os.replace only after validation.
      5. Always clean up the tmp file. On failure, also clean up the rollback
         copy (source was never touched, so it would only waste disk). On
         success the rollback copy is kept on disk so the original bytes can
         still be recovered after the destructive remux.

    Returns a ``(error, rollback_path)`` tuple. On success ``error`` is ``None``
    and ``rollback_path`` points at the kept rollback artifact. On failure
    ``error`` is a short technical code and ``rollback_path`` is ``None``.

    The rollback path is intentionally returned for internal/log use only and
    must not be exposed in API responses (it is a server-side filesystem path).
    """
    if not source.is_file():
        return "local_file_not_found", None
    if not drop_indices:
        return "no_streams_specified", None

    # Pre-flight: refuse the remux before touching the disk if free space on
    # the source filesystem cannot host (rollback copy + FFmpeg tmp output).
    disk_error = _check_remux_disk_space(source)
    if disk_error is not None:
        return disk_error, None

    parent = source.parent
    stem = source.stem
    suffix = source.suffix
    token = uuid.uuid4().hex[:12]
    tmp_path = parent / f".{stem}.remux-{token}{suffix}"
    rollback_path = parent / f".{stem}.rollback-{token}{suffix}"

    # 1) Rollback copy created BEFORE FFmpeg. Refuse the operation if it fails:
    #    we must not run FFmpeg without a recoverable copy of the source.
    try:
        await asyncio.to_thread(shutil.copy2, str(source), str(rollback_path))
    except Exception as exc:  # noqa: BLE001 -- log and refuse, source untouched
        logger.error(f"[opensubtitles] Rollback copy failed for {source}: {exc}")
        _cleanup_path(rollback_path)
        return "backup_failed", None

    # ``shutil.copy2`` preserves the source mtime, which would lie about when
    # the rollback was actually produced. The retention purge buckets rollbacks
    # by mtime, so an old media file would otherwise yield a "born aged"
    # rollback that the next opportunistic sweep deletes immediately. Reset
    # the rollback's atime/mtime to "now" so retention is anchored to the
    # rollback creation, not to the source's last write.
    try:
        await asyncio.to_thread(os.utime, str(rollback_path), None)
    except OSError as exc:
        # Best-effort: failing to touch the timestamps does not invalidate the
        # rollback bytes. The retention helper will then fall back to whatever
        # the filesystem reports — same behaviour as before this fix.
        logger.debug(
            f"[opensubtitles] Failed to refresh rollback mtime for {rollback_path}: {exc}"
        )

    cmd: list[str] = ["ffmpeg", "-i", str(source), "-map", "0"]
    for idx in drop_indices:
        cmd.extend(["-map", f"-0:{idx}"])
    cmd.extend(["-c", "copy", "-y", str(tmp_path)])

    error: str | None = None
    replaced = False
    try:
        # 2) FFmpeg → tmp
        try:
            rc, stderr = await _run_subprocess(cmd, _FFMPEG_TIMEOUT_S)
        except asyncio.TimeoutError:
            logger.error(
                f"[opensubtitles] FFmpeg timeout (>{_FFMPEG_TIMEOUT_S}s) "
                f"removing {drop_indices} from {source}"
            )
            error = "ffmpeg_timeout"
        else:
            if rc != 0:
                full_err = stderr.decode(errors="replace")
                logger.error(
                    f"[opensubtitles] FFmpeg failed (rc={rc}) for {source}\nstderr:\n{full_err}"
                )
                error = f"ffmpeg_failed: {_short_stderr_tail(stderr)}"
            elif not tmp_path.is_file():
                logger.error(f"[opensubtitles] FFmpeg returned 0 but tmp missing: {tmp_path}")
                error = "ffmpeg_no_output"
            else:
                # 3) ffprobe validation on tmp before touching source
                probe_cmd = [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(tmp_path),
                ]
                try:
                    probe_rc, probe_err = await _run_subprocess(probe_cmd, _FFPROBE_TIMEOUT_S)
                except asyncio.TimeoutError:
                    logger.error(f"[opensubtitles] ffprobe timeout for {tmp_path}")
                    error = "ffprobe_timeout"
                else:
                    if probe_rc != 0:
                        full_err = probe_err.decode(errors="replace")
                        logger.error(
                            f"[opensubtitles] ffprobe rejected remux for {source}\nstderr:\n{full_err}"
                        )
                        error = "ffprobe_failed"
                    else:
                        # 4) Atomic replacement only after successful validation.
                        try:
                            os.replace(str(tmp_path), str(source))
                            replaced = True
                        except OSError as exc:
                            logger.error(f"[opensubtitles] os.replace failed for {source}: {exc}")
                            error = "replace_failed"

    except Exception as exc:  # noqa: BLE001 -- catch-all so cleanup runs
        logger.error(f"[opensubtitles] Remux unexpected error for {source}: {exc}")
        error = f"remux_error: {str(exc)[:80]}"
    finally:
        # tmp may have been consumed by os.replace; missing_ok handles that.
        _cleanup_path(tmp_path)
        # On failure, the source was never touched so the rollback copy
        # would only waste disk. On success it is kept as the rollback artifact.
        if not replaced:
            _cleanup_path(rollback_path)

    if replaced:
        logger.info(f"[opensubtitles] Rollback artifact kept for {source} at {rollback_path}")
        # Opportunistic, best-effort retention purge of stale rollback siblings
        # in the same directory. Bounded (single iterdir, strict pattern) and
        # tolerant: any failure is swallowed by the helper so a successful
        # remux is never reported as a failure because of cleanup.
        #
        # Defence in depth: exclude the rollback we just produced even if the
        # earlier ``os.utime`` succeeded. ``shutil.copy2`` preserved the source
        # mtime, and the touch may silently fail on some filesystems (FAT, RO
        # mount, restrictive SMB). The exclusion guarantees the current
        # rollback survives this sweep regardless of mtime, so the safety net
        # promised to the caller is real, not best-effort.
        try:
            await asyncio.to_thread(
                purge_rollback_artifacts,
                parent,
                exclude_paths={rollback_path},
            )
        except Exception as exc:  # noqa: BLE001 -- purge must never fail the remux
            logger.debug(
                f"[opensubtitles] Rollback retention purge skipped for {parent}: {exc}"
            )
        return None, rollback_path
    return error or "remux_error: unknown", None
