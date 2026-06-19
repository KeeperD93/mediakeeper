"""Emby library browsing for the portal: recent, recommended, continue watching."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.settings import (
    get_active_media_source,
    get_emby_public_url,
    get_emby_server_id,
    build_emby_deep_link,
)

logger = logging.getLogger("mediakeeper.portal.available")

_IMG_BASE = "https://image.tmdb.org/t/p"


async def get_recently_added(
    db: AsyncSession, limit: int = 20, *, enrich_rating: bool = False,
) -> list[dict]:
    """Latest items added to Emby.

    ``enrich_rating`` backfills the TMDB rating on items whose Emby payload
    carries no CommunityRating, so the home carousel shows a note like every
    other row. Opt-in: background consumers (digest, trailers) skip it.
    """
    items = await _emby_items(db, {
        "SortBy": "DateCreated",
        "SortOrder": "Descending",
        "IncludeItemTypes": "Movie,Series",
        "Recursive": "true",
        "Limit": str(limit),
        "Fields": "ProviderIds,Overview,DateCreated",
    })
    if enrich_rating:
        await _backfill_tmdb_votes(items, db)
    return items


async def _backfill_tmdb_votes(items: list[dict], db: AsyncSession) -> None:
    """Fill ``vote`` (TMDB rating) on items lacking a usable Emby
    CommunityRating, using the in-memory TMDB meta cache. ``get_meta_cached``
    swallows its own transport errors (returns {}), so one hiccup is harmless.
    """
    from services.tmdb import get_meta_cached
    for it in items:
        if it.get("vote") or not it.get("tmdb_id") or not it.get("media_type"):
            continue
        meta = await get_meta_cached(int(it["tmdb_id"]), it["media_type"], db)
        if meta.get("vote"):
            it["vote"] = meta["vote"]


async def get_recently_added_paginated(
    db: AsyncSession, page: int = 1, page_size: int = 40,
) -> dict:
    """
    Paginated variant of ``get_recently_added`` used by the dedicated
    "Recently added on Emby" browse page.

    Emby supports ``StartIndex`` + ``Limit`` for offset pagination, so we
    turn the 1-based ``page`` into an index, ask for one extra item and
    drop it to derive ``has_more`` without a second round-trip for the
    total count.

    Returns the same shape as ``discover_category`` so the frontend
    ``useInfiniteDiscover`` composable can consume it without branching.
    """
    start = max(0, (page - 1) * page_size)
    # Ask for one extra item so we can tell the caller whether another
    # page exists without needing a second round-trip (Emby exposes a
    # ``TotalRecordCount`` header but querying it adds latency and the
    # count drifts as new items land in the library).
    probe = await _emby_items(db, {
        "SortBy": "DateCreated",
        "SortOrder": "Descending",
        "IncludeItemTypes": "Movie,Series",
        "Recursive": "true",
        "StartIndex": str(start),
        "Limit": str(page_size + 1),
        "Fields": "ProviderIds,Overview,DateCreated",
    })
    has_more = len(probe) > page_size
    items = probe[:page_size]
    return {"items": items, "page": page, "has_more": has_more}


async def get_recommended(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Random items from Emby (pseudo-recommendation)."""
    return await _emby_items(db, {
        "SortBy": "Random",
        "IncludeItemTypes": "Movie,Series",
        "Recursive": "true",
        "Limit": str(limit),
        "Fields": "ProviderIds,Overview",
    })


# ``get_continue_watching`` lives in the sibling module below so this
# file stays under the 300-line rule. Re-exported so existing callers
# keep importing ``available.get_continue_watching``.
from services.portal.available_continue import get_continue_watching  # noqa: F401,E402


async def get_by_genre(
    db: AsyncSession, genre_id: str, limit: int = 20
) -> list[dict]:
    """Items matching a genre (for mood-based navigation)."""
    return await _emby_items(db, {
        "SortBy": "Random",
        "IncludeItemTypes": "Movie,Series",
        "Recursive": "true",
        "GenreIds": genre_id,
        "Limit": str(limit),
        "Fields": "ProviderIds,Overview",
    })


async def get_surprise_pool(
    db: AsyncSession, kind: str, limit: int = 50
) -> list[dict]:
    """
    Return a random pool of items for the Surprise overlay.

    ``kind`` is one of:
      - ``movie``        : ALL movies (live action + animation), excludes
                           documentaries. The "animation" kind was merged
                           into "movie" so users get a single Films tab.
      - ``tv``           : live action TV shows, excludes animation + documentary
      - ``manga``        : animated TV shows (anime / manga series)
      - ``documentary``  : documentaries, movies and shows mixed

    Each item is already enriched with ``emby_url`` (public HTTPS link
    when configured) and ``availability`` so the frontend MediaCard
    can render the "Start" button without a second lookup.
    """
    # Mapping of UX kinds onto Emby query params.
    KIND_MAP = {
        "movie": {
            "IncludeItemTypes": "Movie",
            "ExcludeGenres": "Documentary",
        },
        "tv": {
            "IncludeItemTypes": "Series",
            "ExcludeGenres": "Animation|Documentary",
        },
        "manga": {
            "IncludeItemTypes": "Series",
            "Genres": "Animation",
        },
        "documentary": {
            "IncludeItemTypes": "Movie,Series",
            "Genres": "Documentary",
        },
    }
    params = KIND_MAP.get(kind)
    if not params:
        return []

    return await _emby_items(db, {
        **params,
        "SortBy": "Random",
        "Recursive": "true",
        "Limit": str(limit),
        "Fields": "ProviderIds,Overview,PremiereDate,RunTimeTicks,CommunityRating",
    })


async def _emby_items(db: AsyncSession, params: dict) -> list[dict]:
    cfg = await _get_config(db)
    if not cfg:
        return []
    url, api_key = cfg
    # Use the public URL for user-facing deep links; fall back to the
    # internal URL when no public URL is configured.
    source = await get_active_media_source(db)
    public_url = get_emby_public_url(source) if source else ""
    server_id = await get_emby_server_id(source) if source else ""
    client = get_internal_client()
    try:
        res = await client.get(
            f"{url}/Items", params=params,
            headers={"X-Emby-Token": api_key},
        )
        if res.status_code != 200:
            return []
        return [_normalize_emby(item, public_url, server_id) for item in res.json().get("Items", [])]
    except Exception as e:
        logger.error(f"[AVAILABLE] Error: {e}")
        return []


async def _get_config(db: AsyncSession):
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return None
    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return None
    return url, api_key


def _normalize_emby(item: dict, public_url: str = "", server_id: str = "") -> dict:
    providers = item.get("ProviderIds", {})
    tmdb_id = providers.get("Tmdb") or providers.get("tmdb")
    item_type = item.get("Type", "")
    media_type = "tv" if item_type == "Series" else "movie"
    emby_id = item.get("Id", "")

    # Items surfaced by this module come straight from the Emby library,
    # so they are by definition available. Stamp emby_url + availability
    # so MediaCard can show the green dot and the "Watch" button
    # without going through the tmdb-id based availability lookup.
    emby_url = build_emby_deep_link(public_url, emby_id, server_id)

    # Runtime comes from Emby as 100-nanosecond "ticks"; divide by
    # 600_000_000 to get minutes (1 second = 10_000_000 ticks).
    ticks = item.get("RunTimeTicks") or 0
    runtime_minutes = int(ticks / 600_000_000) if ticks else 0

    premiere = item.get("PremiereDate") or ""
    release_date = premiere[:10] if premiere else ""

    vote = item.get("CommunityRating")
    try:
        vote = round(float(vote), 1) if vote is not None else 0
    except (TypeError, ValueError):
        vote = 0

    # Emby returns DateCreated as ISO-8601 (UTC). ``date_created`` keeps the
    # "YYYY-MM-DD" prefix (enough for the frontend "New on Emby" ribbon to
    # compute "less than 7 days old" locally without timezone headaches);
    # ``date_created_at`` keeps the full timestamp for sub-day comparisons
    # (e.g. the digest "added since you last caught up" watermark).
    date_created_raw = item.get("DateCreated") or ""
    date_created = date_created_raw[:10] if date_created_raw else ""

    return {
        "id": tmdb_id or emby_id,
        "emby_item_id": emby_id,
        "tmdb_id": int(tmdb_id) if tmdb_id else None,
        "title": item.get("Name", ""),
        "year": str(item.get("ProductionYear", "")),
        "overview": item.get("Overview", ""),
        "poster_url": f"/api/emby/image/{emby_id}?type=Primary" if emby_id else "",
        "backdrop": f"/api/emby/image/{emby_id}?type=Backdrop" if emby_id else "",
        "media_type": media_type,
        "emby_url": emby_url,
        "availability": "full",
        "runtime": runtime_minutes,
        "release_date": release_date,
        "date_created": date_created,
        "date_created_at": date_created_raw,
        "vote": vote,
    }
