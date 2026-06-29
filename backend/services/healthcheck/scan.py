"""Scan full HealthCheck : parcourt Emby et alimente la table des results."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.healthcheck import HealthCheckResult
from services.settings import get_active_media_source

from ._analyze import _analyze_item, _max_severity
from .config import _load_config

logger = logging.getLogger("mediakeeper.healthcheck")

_scan_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_item": "",
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def get_scan_status() -> dict:
    return {**_scan_state}


async def _load_library_map(client, url: str, headers: dict) -> dict:
    """Preload Emby libraries to map ParentId -> name."""
    lib_map: dict[str, str] = {}
    try:
        libs_res = await client.get(f"{url}/Library/VirtualFolders", headers=headers, timeout=10.0)
        if libs_res.status_code == 200:
            for vf in libs_res.json():
                vf_name = vf.get("Name", "")
                vf_id = vf.get("ItemId", "")
                if vf_id and vf_name:
                    lib_map[vf_id] = vf_name
    except Exception:
        logger.warning("[healthcheck] Could not load Emby libraries for mapping")
    return lib_map


def _resolve_library(item: dict, lib_map: dict) -> str:
    for field in ("LibraryName", "ParentId", "TopParentId"):
        val = item.get(field) or ""
        if field == "LibraryName" and val:
            return val
        if val and val in lib_map:
            return lib_map[val]
    return ""


async def run_healthcheck(db: AsyncSession, progress_cb=None) -> dict:
    """Start a full health scan across all libraries."""
    global _scan_state

    if _scan_state["running"]:
        return {"error": "scan_already_running"}

    _scan_state.update(running=True, progress=0, total=0, current_item="",
                       started_at=datetime.now(timezone.utc).isoformat(),
                       finished_at=None, error=None)

    config = await _load_config(db)

    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        _scan_state.update(running=False, error="no_source")
        return {"error": "no_source"}

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()

        count_res = await client.get(f"{url}/Items", params={
            "IncludeItemTypes": "Movie,Episode",
            "Recursive": "true",
            "Limit": 0,
        }, headers=headers, timeout=15.0)

        total_items = count_res.json().get("TotalRecordCount", 0) if count_res.status_code == 200 else 0
        _scan_state["total"] = total_items

        if total_items == 0:
            _scan_state.update(running=False, finished_at=datetime.now(timezone.utc).isoformat())
            return {"scanned": 0, "issues": 0}

        lib_map = await _load_library_map(client, url, headers)

        batch_size = 100
        scanned = 0
        total_issues = 0
        pending_results: list[dict] = []

        for offset in range(0, total_items, batch_size):
            res = await client.get(f"{url}/Items", params={
                "IncludeItemTypes": "Movie,Episode",
                "Recursive": "true",
                "Fields": "MediaSources,MediaStreams,Path",
                "SortBy": "SortName",
                "SortOrder": "Ascending",
                "StartIndex": offset,
                "Limit": batch_size,
            }, headers=headers, timeout=30.0)

            if res.status_code != 200:
                logger.warning(f"[healthcheck] Emby returned {res.status_code} at offset {offset}")
                continue

            items = res.json().get("Items", [])

            for item in items:
                item_name = item.get("Name") or "?"
                _scan_state["current_item"] = item_name
                scanned += 1
                _scan_state["progress"] = scanned
                if progress_cb and scanned % 50 == 0:
                    progress_cb(scanned, total_items, item_name)

                issues = _analyze_item(item, config)
                if not issues:
                    continue

                series = item.get("SeriesName")
                lib = _resolve_library(item, lib_map)

                path = ""
                sources = item.get("MediaSources") or []
                if sources:
                    path = sources[0].get("Path") or ""

                pending_results.append({
                    "item_id": item.get("Id", ""),
                    "item_name": item_name,
                    "item_type": item.get("Type", ""),
                    "series_id": item.get("SeriesId") or None,
                    "series_name": series,
                    "season_num": item.get("ParentIndexNumber"),
                    "episode_num": item.get("IndexNumber"),
                    "library_name": lib,
                    "issues": json.dumps(issues),
                    "severity": _max_severity(issues),
                    "file_path": path,
                })
                total_issues += len(issues)

            await asyncio.sleep(0.1)

        await db.execute(delete(HealthCheckResult))
        if pending_results:
            db.add_all(HealthCheckResult(**row) for row in pending_results)
        await db.commit()

        _scan_state.update(
            running=False,
            current_item="",
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(f"[healthcheck] Scan complete : {scanned} items, {total_issues} issues")
        return {"scanned": scanned, "issues": total_issues}

    except Exception as e:
        if db.in_transaction():
            await db.rollback()
        logger.exception("[healthcheck] Error scan: %s", e)
        _scan_state.update(running=False, error=str(e)[:500])
        return {"error": str(e)[:500]}
