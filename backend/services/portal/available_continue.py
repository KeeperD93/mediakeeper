"""Continue-watching carousel builder — extracted from ``available.py``
to stay under the 300-line rule. Episodes collapse into their parent
series so the user sees one poster per show, and anything without a
TMDB match or without an Emby poster is dropped so the strip stays
clean."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.settings import (
    get_active_media_source,
    get_emby_public_url,
    get_emby_server_id,
)

logger = logging.getLogger("mediakeeper.portal.available")


async def get_continue_watching(
    db: AsyncSession, emby_user_id: str | None = None, limit: int = 10,
) -> list[dict]:
    """Items in progress for one Emby user.

    Returns an empty list when no Emby user id is supplied: querying the
    server-wide ``/Items`` with the admin API key would leak every user's
    in-progress titles to the caller. Fail closed on cross-user isolation.
    """
    if not emby_user_id:
        return []
    # Lazy import to avoid a circular import with ``available`` (which
    # re-exports this function).
    from services.portal.available import _get_config, _normalize_emby

    cfg = await _get_config(db)
    if not cfg:
        return []
    url, api_key = cfg
    source = await get_active_media_source(db)
    public_url = get_emby_public_url(source) if source else ""
    server_id = await get_emby_server_id(source) if source else ""
    client = get_internal_client()
    headers = {"X-Emby-Token": api_key}

    try:
        params = {
            "SortBy": "DatePlayed",
            "SortOrder": "Descending",
            "Filters": "IsResumable",
            "Recursive": "true",
            "IncludeItemTypes": "Movie,Episode",
            # Ask for more raw items than we'll ship so there's enough
            # material after collapsing episodes into series.
            "Limit": str(max(limit * 4, 30)),
            "Fields": "ProviderIds,Overview,SeriesId,SeriesName,ImageTags",
        }
        endpoint = f"{url}/Users/{emby_user_id}/Items"
        res = await client.get(endpoint, params=params, headers=headers)
        if res.status_code != 200:
            return []
        raw = res.json().get("Items", []) or []
    except Exception as e:
        logger.error("[AVAILABLE] continue watching error: %s", e)
        return []

    # Unique series ids for a single bulk fetch of series metadata.
    seen_series: set[str] = set()
    series_ids: list[str] = []
    for it in raw:
        if it.get("Type") == "Episode":
            sid = it.get("SeriesId")
            if sid and sid not in seen_series:
                seen_series.add(sid)
                series_ids.append(sid)

    series_meta: dict[str, dict] = {}
    if series_ids:
        try:
            s_res = await client.get(
                f"{url}/Items",
                params={"Ids": ",".join(series_ids), "Fields": "ProviderIds,ImageTags"},
                headers=headers, timeout=10.0,
            )
            if s_res.status_code == 200:
                for item in s_res.json().get("Items", []):
                    series_meta[item.get("Id", "")] = item
        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
            pass

    out: list[dict] = []
    emitted_ids: set[str] = set()
    for it in raw:
        item_type = it.get("Type", "")
        if item_type == "Movie":
            entry = _normalize_emby(it, public_url, server_id)
            has_image = bool((it.get("ImageTags") or {}).get("Primary"))
        elif item_type == "Episode":
            sid = it.get("SeriesId")
            meta = series_meta.get(sid or "")
            if not meta:
                continue
            entry = _normalize_emby({
                "Id": sid, "Type": "Series",
                "Name": it.get("SeriesName") or meta.get("Name", ""),
                "ProviderIds": meta.get("ProviderIds") or {},
                "ImageTags": meta.get("ImageTags") or {},
                "ProductionYear": meta.get("ProductionYear"),
                "Overview": meta.get("Overview") or "",
                "CommunityRating": meta.get("CommunityRating"),
                "PremiereDate": meta.get("PremiereDate") or "",
            }, public_url, server_id)
            has_image = bool((meta.get("ImageTags") or {}).get("Primary"))
        else:
            continue
        if not entry.get("tmdb_id") or not has_image:
            continue
        if entry["emby_item_id"] in emitted_ids:
            continue
        emitted_ids.add(entry["emby_item_id"])
        out.append(entry)
        if len(out) >= limit:
            break
    return out
