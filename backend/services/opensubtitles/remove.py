"""Deletion de pistes (audio/sous-titres embedded) via remux ffmpeg."""
import asyncio
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from ._constants import logger
from .paths import _resolve_local_path
from .streams import _extract_first_emby_item


async def remove_stream(
    db: AsyncSession,
    item_id: str,
    stream_index: int,
) -> dict:
    """Supprime un stream (audio ou sous-titre embedded) d'un file media via ffmpeg remux.

    1. Identifie le file et le stream
    2. Remux with ffmpeg en excluant le stream
    3. Replace l'original
    4. Refresh Emby
    """
    from services.emby import _get_emby_config

    cfg = await _get_emby_config(db)
    if not cfg:
        return {"error": "emby_not_configured"}

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
            return {"error": f"emby_error_{res.status_code}"}

        item_data = _extract_first_emby_item(res.json())
        if not item_data:
            return {"error": "item_not_found"}
        sources = item_data.get("MediaSources") or []
        if not sources:
            return {"error": "no_media_source"}

        file_path = sources[0].get("Path", "")
        if not file_path:
            return {"error": "no_file_path"}
        local_path = await _resolve_local_path(db, file_path)
        if not local_path or not Path(local_path).exists():
            return {"error": "local_file_not_found"}

        media_streams = sources[0].get("MediaStreams", [])
        target_stream = None
        for s in media_streams:
            if s.get("Index") == stream_index:
                target_stream = s
                break

        if not target_stream:
            return {"error": "stream_not_found"}

        stream_type = target_stream.get("Type", "")
        if stream_type not in ("Audio", "Subtitle"):
            return {"error": "invalid_stream_type"}

        if target_stream.get("IsExternal"):
            return {"error": "use_delete_external_for_external_subs"}

    except Exception as e:
        return {"error": str(e)[:200]}

    p = Path(local_path)
    tmp_path = str(p.with_suffix(f".tmp{p.suffix}"))

    try:
        cmd = [
            "ffmpeg", "-i", local_path,
            "-map", "0",
            "-map", f"-0:{stream_index}",
            "-c", "copy",
            "-y", tmp_path,
        ]

        logger.info(f"[opensubtitles] Removing stream {stream_index} ({stream_type}) from {local_path}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                pass
            err_msg = stderr.decode(errors="replace")[-300:] if stderr else "unknown"
            logger.error(f"[opensubtitles] ffmpeg failed: {err_msg}")
            return {"error": f"ffmpeg_failed: {err_msg[:100]}"}

        shutil.move(tmp_path, local_path)
        logger.info(f"[opensubtitles] Stream {stream_index} removed successfully")

        try:
            await client.post(
                f"{url}/Items/{item_id}/Refresh",
                headers=headers, timeout=10.0,
            )
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass

        return {
            "success": True,
            "removed_stream": stream_index,
            "stream_type": stream_type.lower(),
            "language": target_stream.get("Language", "?"),
        }

    except asyncio.TimeoutError:
        Path(tmp_path).unlink(missing_ok=True)
        return {"error": "ffmpeg_timeout"}
    except Exception as e:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass
        logger.error(f"[opensubtitles] Remove stream error: {e}")
        return {"error": str(e)[:200]}


async def remove_streams_batch(
    db: AsyncSession,
    item_id: str,
    stream_indices: list[int],
) -> dict:
    """Supprime several streams en un seul remux ffmpeg (much plus rapide)."""
    from services.emby import _get_emby_config

    if not stream_indices:
        return {"error": "no_streams_specified"}

    cfg = await _get_emby_config(db)
    if not cfg:
        return {"error": "emby_not_configured"}

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
            return {"error": f"emby_error_{res.status_code}"}

        item_data = _extract_first_emby_item(res.json())
        if not item_data:
            return {"error": "item_not_found"}
        sources = item_data.get("MediaSources") or []
        if not sources:
            return {"error": "no_media_source"}

        file_path = sources[0].get("Path", "")
        if not file_path:
            return {"error": "no_file_path"}
        local_path = await _resolve_local_path(db, file_path)
        if not local_path or not Path(local_path).exists():
            return {"error": "local_file_not_found"}

        media_streams = sources[0].get("MediaStreams", [])
        valid_indices = {s.get("Index") for s in media_streams if s.get("Type") in ("Audio", "Subtitle") and not s.get("IsExternal")}
        to_remove = [i for i in stream_indices if i in valid_indices]
        if not to_remove:
            return {"error": "no_valid_streams"}

    except Exception as e:
        return {"error": str(e)[:200]}

    p = Path(local_path)
    tmp_path = str(p.with_suffix(f".tmp{p.suffix}"))

    try:
        cmd = ["ffmpeg", "-i", local_path, "-map", "0"]
        for idx in to_remove:
            cmd.extend(["-map", f"-0:{idx}"])
        cmd.extend(["-c", "copy", "-y", tmp_path])

        logger.info(f"[opensubtitles] Batch removing streams {to_remove} from {local_path}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            Path(tmp_path).unlink(missing_ok=True)
            err_msg = stderr.decode(errors="replace")[-300:] if stderr else "unknown"
            logger.error(f"[opensubtitles] ffmpeg batch failed: {err_msg}")
            return {"error": f"ffmpeg_failed: {err_msg[:100]}"}

        shutil.move(tmp_path, local_path)
        logger.info(f"[opensubtitles] {len(to_remove)} streams removed successfully")

        try:
            await client.post(f"{url}/Items/{item_id}/Refresh", headers=headers, timeout=10.0)
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass

        return {"success": True, "removed_count": len(to_remove), "removed_streams": to_remove}

    except asyncio.TimeoutError:
        Path(tmp_path).unlink(missing_ok=True)
        return {"error": "ffmpeg_timeout"}
    except Exception as e:
        Path(tmp_path).unlink(missing_ok=True)
        logger.error(f"[opensubtitles] Batch remove error: {e}")
        return {"error": str(e)[:200]}
