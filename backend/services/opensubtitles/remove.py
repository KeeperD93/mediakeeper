"""Public API: delete embedded audio/subtitle streams via a safe FFmpeg remux.

The low-level remux flow (subprocess plumbing, disk-space guard, atomic
replacement, rollback creation) lives in :mod:`._remux`. This module owns the
orchestration: resolving the local file from Emby metadata, calling the safe
remux, and refreshing Emby on success.
"""
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from ._constants import logger
from ._remux import _safe_remux
from .paths import _resolve_local_path
from .streams import _extract_first_emby_item


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
    except Exception:
        logger.exception("[opensubtitles] Resolve remove target failed")
        return {}, {"error": "resolve_target_failed"}


async def _refresh_emby(client, url: str, headers: dict, item_id: str) -> None:
    try:
        await client.post(
            f"{url}/Items/{item_id}/Refresh",
            headers=headers, timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001 -- refresh is best-effort
        logger.debug("[opensubtitles] Emby refresh failed for %s: %s", item_id, exc)


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
        "[opensubtitles] Removing stream %s (%s) from %s",
        stream_index, stream_type, local_path,
    )

    failure, rollback_path = await _safe_remux(Path(local_path), [stream_index])
    if failure is not None:
        return {"error": failure}

    logger.info("[opensubtitles] Stream %s removed successfully", stream_index)

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
    logger.info(
        "[opensubtitles] Batch removing streams %s from %s", to_remove, local_path,
    )

    failure, rollback_path = await _safe_remux(Path(local_path), to_remove)
    if failure is not None:
        return {"error": failure}

    logger.info("[opensubtitles] %s streams removed successfully", len(to_remove))

    await _refresh_emby(ctx["client"], ctx["url"], ctx["headers"], item_id)

    return {
        "success": True,
        "removed_count": len(to_remove),
        "removed_streams": to_remove,
        # Non-sensitive flag: signals a rollback artifact exists server-side.
        # The actual filesystem path is intentionally not exposed here.
        "rollback_kept": rollback_path is not None,
    }
