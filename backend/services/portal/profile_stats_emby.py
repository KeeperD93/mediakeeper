"""Emby helpers shared by the profile_stats modules.

Extracted from ``profile_stats_recent.py`` to keep that file under the
300-line file-size convention. Both ``fetch_recent_watches`` and
``fetch_next_to_finish`` need to poster-check and series-id-resolve,
so the helpers live in their own module now.
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.playback_stats import PlaybackSession


async def resolve_emby_user_id(
    db: AsyncSession, user_filter,
) -> str | None:
    """Find the most-used Emby user_id for the given Portal user.

    PlaybackSession.user_id stores the raw Emby UUID. We pick the most
    frequent value matching the user/profile filter (a single profile
    can in theory have multiple Emby accounts wired up over time, but
    the dominant one is the real owner of the library state)."""
    try:
        row = (await db.execute(
            select(
                PlaybackSession.user_id,
                func.count(PlaybackSession.id).label("c"),
            )
            .where(user_filter)
            .group_by(PlaybackSession.user_id)
            .order_by(func.count(PlaybackSession.id).desc())
            .limit(1)
        )).first()
        if row and row.user_id:
            return row.user_id
    except Exception:
        pass
    return None


async def _bulk_fetch_emby_info(
    item_ids: list[str], emby_url: str, emby_key: str,
) -> dict[str, dict]:
    """Fetch `{emby_id: {has_image, tmdb_id}}` in a single Items call.
    Needed by the profile carousels so MediaCard clicks land on the
    right TMDB detail page (Emby IDs aren't routable by themselves)."""
    if not item_ids or not emby_url or not emby_key:
        return {}
    try:
        res = await get_internal_client().get(
            f"{emby_url}/Items",
            params={"Ids": ",".join(item_ids), "Fields": "ImageTags,ProviderIds"},
            headers={"X-Emby-Token": emby_key},
            timeout=10.0,
        )
        if res.status_code != 200:
            return {}
        out: dict[str, dict] = {}
        for item in res.json().get("Items", []):
            iid = item.get("Id")
            if not iid:
                continue
            tags = item.get("ImageTags") or {}
            providers = item.get("ProviderIds") or {}
            tmdb_raw = providers.get("Tmdb") or providers.get("tmdb")
            try:
                tmdb_id = int(tmdb_raw) if tmdb_raw is not None else None
            except (TypeError, ValueError):
                tmdb_id = None
            out[iid] = {
                "has_image": bool(tags.get("Primary")),
                "tmdb_id": tmdb_id,
            }
        return out
    except Exception:
        return {}


async def _find_series_emby_id(
    series_name: str, emby_url: str, emby_key: str,
) -> str | None:
    """Search Emby for a Series item by name and return its ID."""
    client = get_internal_client()
    try:
        res = await client.get(
            f"{emby_url}/Items",
            params={
                "SearchTerm": series_name,
                "IncludeItemTypes": "Series",
                "Recursive": "true",
                "Limit": "1",
            },
            headers={"X-Emby-Token": emby_key},
        )
        if res.status_code == 200:
            items = (res.json() or {}).get("Items", [])
            if items:
                return items[0].get("Id", "")
    except Exception:
        pass
    return None
