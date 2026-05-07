"""Deletion de pistes (audio/sous-titres embedded) via remux ffmpeg."""
import asyncio
import os
import shutil
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from ._constants import logger
from .paths import _resolve_local_path
from .streams import _extract_first_emby_item

_FFMPEG_TIMEOUT_S = 300
_FFPROBE_TIMEOUT_S = 30


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
        return None, rollback_path
    return error or "remux_error: unknown", None


async def _resolve_remove_target(
    db: AsyncSession,
    item_id: str,
    *,
    require_indices: list[int] | None = None,
    require_single: int | None = None,
) -> tuple[dict, dict | None]:
    """Resolve the local file + target streams. Returns (ctx, error_dict)."""
    from services.emby import _get_emby_config

    cfg = await _get_emby_config(db)
    if not cfg:
        return {}, {"error": "emby_not_configured"}

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    client = get_internal_client()

    try:
        res = await client.get(
            f"{url}/Items",
            params={"Ids": item_id, "Fields": "MediaSources,MediaStreams,Path", "Limit": "1"},
            headers=headers, timeout=10.0,
        )
        if res.status_code != 200:
            return {}, {"error": f"emby_error_{res.status_code}"}

        item_data = _extract_first_emby_item(res.json())
        if not item_data:
            return {}, {"error": "item_not_found"}
        sources = item_data.get("MediaSources") or []
        if not sources:
            return {}, {"error": "no_media_source"}

        file_path = sources[0].get("Path", "")
        if not file_path:
            return {}, {"error": "no_file_path"}
        local_path = await _resolve_local_path(db, file_path)
        if not local_path or not Path(local_path).exists():
            return {}, {"error": "local_file_not_found"}

        media_streams = sources[0].get("MediaStreams", [])

        ctx = {
            "url": url,
            "headers": headers,
            "client": client,
            "local_path": local_path,
            "media_streams": media_streams,
        }

        if require_single is not None:
            target_stream = next(
                (s for s in media_streams if s.get("Index") == require_single),
                None,
            )
            if not target_stream:
                return {}, {"error": "stream_not_found"}
            stream_type = target_stream.get("Type", "")
            if stream_type not in ("Audio", "Subtitle"):
                return {}, {"error": "invalid_stream_type"}
            if target_stream.get("IsExternal"):
                return {}, {"error": "use_delete_external_for_external_subs"}
            ctx["target_stream"] = target_stream

        if require_indices is not None:
            valid_indices = {
                s.get("Index") for s in media_streams
                if s.get("Type") in ("Audio", "Subtitle") and not s.get("IsExternal")
            }
            ctx["to_remove"] = [i for i in require_indices if i in valid_indices]

        return ctx, None
    except Exception as exc:  # noqa: BLE001 -- map to short error
        return {}, {"error": str(exc)[:200]}


async def _refresh_emby(client, url: str, headers: dict, item_id: str) -> None:
    try:
        await client.post(
            f"{url}/Items/{item_id}/Refresh",
            headers=headers, timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001 -- refresh is best-effort
        logger.debug(f"[opensubtitles] Emby refresh failed for {item_id}: {exc}")


async def remove_stream(
    db: AsyncSession,
    item_id: str,
    stream_index: int,
) -> dict:
    """Delete a single embedded stream (audio or subtitle) via a safe FFmpeg remux."""
    ctx, err = await _resolve_remove_target(db, item_id, require_single=stream_index)
    if err:
        return err

    local_path = ctx["local_path"]
    target_stream = ctx["target_stream"]
    stream_type = target_stream.get("Type", "")

    logger.info(
        f"[opensubtitles] Removing stream {stream_index} ({stream_type}) from {local_path}"
    )

    failure, rollback_path = await _safe_remux(Path(local_path), [stream_index])
    if failure is not None:
        return {"error": failure}

    logger.info(f"[opensubtitles] Stream {stream_index} removed successfully")

    await _refresh_emby(ctx["client"], ctx["url"], ctx["headers"], item_id)

    return {
        "success": True,
        "removed_stream": stream_index,
        "stream_type": stream_type.lower(),
        "language": target_stream.get("Language", "?"),
        # Non-sensitive flag: signals a rollback artifact exists server-side.
        # The actual filesystem path is intentionally not exposed here.
        "rollback_kept": rollback_path is not None,
    }


async def remove_streams_batch(
    db: AsyncSession,
    item_id: str,
    stream_indices: list[int],
) -> dict:
    """Delete several embedded streams in a single safe FFmpeg remux."""
    if not stream_indices:
        return {"error": "no_streams_specified"}

    ctx, err = await _resolve_remove_target(db, item_id, require_indices=stream_indices)
    if err:
        return err

    to_remove = ctx.get("to_remove") or []
    if not to_remove:
        return {"error": "no_valid_streams"}

    local_path = ctx["local_path"]
    logger.info(f"[opensubtitles] Batch removing streams {to_remove} from {local_path}")

    failure, rollback_path = await _safe_remux(Path(local_path), to_remove)
    if failure is not None:
        return {"error": failure}

    logger.info(f"[opensubtitles] {len(to_remove)} streams removed successfully")

    await _refresh_emby(ctx["client"], ctx["url"], ctx["headers"], item_id)

    return {
        "success": True,
        "removed_count": len(to_remove),
        "removed_streams": to_remove,
        # Non-sensitive flag: signals a rollback artifact exists server-side.
        # The actual filesystem path is intentionally not exposed here.
        "rollback_kept": rollback_path is not None,
    }
