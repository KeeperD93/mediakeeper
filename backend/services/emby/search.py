"""Emby search helpers used by the ticket creation autocomplete.

Tickets must point to a real library item, not free-text — so the picker
queries Emby directly. We restrict types to ``Movie`` and ``Series`` (the
caller drills into seasons/episodes via ``list_series_seasons``) and only
return the fields the UI needs: id, title, year, image ids, kind.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client

from .config import _get_emby_config

logger = logging.getLogger("mediakeeper.emby.search")


def _premiere_year(item: dict) -> str | None:
    year = item.get("ProductionYear")
    if year:
        return str(year)
    premiere = item.get("PremiereDate") or ""
    return premiere[:4] or None


def _shape_search_hit(item: dict) -> dict:
    """Reduce an Emby item to the shape the ticket picker consumes."""
    item_id = item.get("Id")
    return {
        "id": item_id,
        "type": "series" if item.get("Type") == "Series" else "movie",
        "title": item.get("Name") or "",
        "original_title": item.get("OriginalTitle") or None,
        "year": _premiere_year(item),
        # The frontend builds the URL itself via /api/emby/image/{id} — we
        # only return ids so the proxy can be cached/auth-checked centrally.
        "poster_id": item_id,
        "backdrop_id": item_id,
        "tmdb_id": (item.get("ProviderIds") or {}).get("Tmdb"),
    }


async def search_movies_and_series(
    db: AsyncSession, query: str, *, limit: int = 10
) -> list[dict]:
    """Search Emby for movies and series matching ``query``.

    Episodes are intentionally excluded — the picker shows series as a
    single hit, then ``list_series_seasons`` opens the season/episode tree.
    Empty/missing config returns an empty list rather than raising, so the
    UI degrades to "no results" instead of erroring out the user.
    """
    query = (query or "").strip()
    if not query:
        return []

    cfg = await _get_emby_config(db)
    if not cfg:
        return []

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Items",
            params={
                "SearchTerm": query,
                "IncludeItemTypes": "Movie,Series",
                "Recursive": "true",
                "Limit": limit,
                "Fields": "ProviderIds,PremiereDate,ProductionYear,OriginalTitle",
            },
            headers=headers,
            timeout=10.0,
        )
        if res.status_code != 200:
            return []
        items = res.json().get("Items", [])
        return [_shape_search_hit(it) for it in items if it.get("Id")]
    except Exception as e:
        logger.error(f"Error search_movies_and_series: {e}")
        return []


async def list_series_seasons(
    db: AsyncSession, series_id: str
) -> list[dict]:
    """Return seasons of a series with their episode list.

    Shape:
    ``[{"season_number": 1, "name": "Saison 1", "episodes":
        [{"episode_number": 1, "name": "Pilot", "id": "..."}, ...]}, ...]``
    Specials (``ParentIndexNumber == 0``) are kept — users may legitimately
    file tickets against them.
    """
    if not series_id:
        return []

    cfg = await _get_emby_config(db)
    if not cfg:
        return []

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}

    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Shows/{series_id}/Seasons",
            params={"Fields": "IndexNumber"},
            headers=headers,
            timeout=10.0,
        )
        if res.status_code != 200:
            return []
        seasons = res.json().get("Items", [])

        out: list[dict] = []
        for season in seasons:
            season_num = season.get("IndexNumber")
            if season_num is None:
                continue
            episodes = await _list_season_episodes(
                client, url, headers, series_id, season.get("Id")
            )
            out.append({
                "season_number": season_num,
                "name": season.get("Name") or f"Season {season_num}",
                "episodes": episodes,
            })
        out.sort(key=lambda s: s["season_number"])
        return out
    except Exception as e:
        logger.error(f"Error list_series_seasons({series_id}): {e}")
        return []


async def _list_season_episodes(
    client, url: str, headers: dict, series_id: str, season_id: str
) -> list[dict]:
    if not season_id:
        return []
    try:
        res = await client.get(
            f"{url}/Shows/{series_id}/Episodes",
            params={
                "SeasonId": season_id,
                "Fields": "IndexNumber,Name",
            },
            headers=headers,
            timeout=10.0,
        )
        if res.status_code != 200:
            return []
        items = res.json().get("Items", [])
        episodes = [
            {
                "id": ep.get("Id"),
                "episode_number": ep.get("IndexNumber"),
                "name": ep.get("Name") or "",
            }
            for ep in items
            if ep.get("IndexNumber") is not None
        ]
        episodes.sort(key=lambda e: e["episode_number"])
        return episodes
    except Exception as e:
        logger.error(f"Error _list_season_episodes(series={series_id}, season={season_id}): {e}")
        return []
