"""Top 20 most played media this month — same logic as stats_aggregator.

The URL route, the function name and the tags are intentionally kept
as ``top20`` so the frontend and any external consumers that already
hit ``/api/portal/top20`` keep working unchanged. Only the file and
the logger scope were renamed to reflect the real rank depth (20).
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.http_client import get_internal_client
from models.user import User
from models.portal.profile import UserProfile
from models.playback_stats import PlaybackSession
from api.portal.deps import get_current_profile
from services.settings import (
    get_active_media_source,
    get_emby_public_url,
    get_emby_server_id,
    build_emby_deep_link,
)

router = APIRouter(prefix="/top20", tags=["portal-top20"])
logger = logging.getLogger("mediakeeper.portal.top20")

_series_id_cache: dict[str, str] = {}


async def _find_series_id(series_name: str, url: str, api_key: str) -> str | None:
    """Find the Emby Series item ID by name for poster lookup."""
    if series_name in _series_id_cache:
        return _series_id_cache[series_name]
    client = get_internal_client()
    try:
        res = await client.get(
            f"{url}/Items",
            params={
                "SearchTerm": series_name,
                "IncludeItemTypes": "Series",
                "Recursive": "true",
                "Limit": "1",
            },
            headers={"X-Emby-Token": api_key},
        )
        if res.status_code == 200:
            items = res.json().get("Items", [])
            if items:
                sid = items[0].get("Id", "")
                _series_id_cache[series_name] = sid
                return sid
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass
    return None


@router.get("")
async def get_top20(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Top 20 most played items this month (movies + series mixed).

    Name kept as ``top20`` for URL backwards-compatibility with
    existing clients / links, but the row is rendered as "Top 20 du
        mois sur Emby" on the Portal home. The merge pulls 20 movies
    and 20 series, sorts by play count, and returns the top 20 of
    the combined list — so a dominant-movies month still surfaces
    up to 20 movies, and a series-heavy month up to 20 series.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get Emby config for series poster lookup. ``emby_url`` is the
    # internal URL used by the backend itself; ``public_url`` is what
    # we hand out in user-facing deep links (HTTPS when configured).
    source = await get_active_media_source(db)
    emby_url = ""
    emby_key = ""
    if source and source.get("source") in ("emby", "jellyfin"):
        emby_url = source.get("url", "").rstrip("/")
        emby_key = source.get("api_key", "")
    public_url = get_emby_public_url(source) if source else ""
    server_id = await get_emby_server_id(source) if source else ""

    def _watch_link(item_id: str | None) -> str:
        return build_emby_deep_link(public_url, item_id, server_id)

    # Top movies
    movies_q = await db.execute(
        select(
            PlaybackSession.item_name,
            PlaybackSession.item_id,
            func.count(PlaybackSession.id).label("play_count"),
        )
        .where(
            PlaybackSession.item_type == "Movie",
            PlaybackSession.started_at >= month_start,
        )
        .group_by(PlaybackSession.item_name, PlaybackSession.item_id)
        .order_by(desc("play_count"))
        .limit(20)
    )

    items = []
    for r in movies_q.all():
        items.append({
            "id": r.item_id,
            "emby_item_id": r.item_id,
            "title": r.item_name,
            "media_type": "movie",
            "play_count": r.play_count,
            "poster_url": f"/api/emby/image/{r.item_id}?type=Primary",
            # Pre-computed deep link + availability so MediaCard can render
            # the green "Regarder" button + the green dot without an extra
            # availability lookup (Top 20 items are always in Emby).
            "emby_url": _watch_link(r.item_id),
            "availability": "full",
        })

    # Top series — find the Series ID for proper poster
    series_q = await db.execute(
        select(
            PlaybackSession.series_name,
            func.count(PlaybackSession.id).label("play_count"),
        )
        .where(
            PlaybackSession.item_type == "Episode",
            PlaybackSession.series_name.isnot(None),
            PlaybackSession.started_at >= month_start,
        )
        .group_by(PlaybackSession.series_name)
        .order_by(desc("play_count"))
        .limit(20)
    )

    for r in series_q.all():
        series_id = None
        if emby_url and emby_key:
            series_id = await _find_series_id(r.series_name, emby_url, emby_key)

        poster_id = series_id or ""
        items.append({
            "id": series_id or r.series_name,
            "emby_item_id": series_id,
            "title": r.series_name,
            "media_type": "tv",
            "play_count": r.play_count,
            "poster_url": f"/api/emby/image/{poster_id}?type=Primary" if poster_id else "",
            "emby_url": _watch_link(series_id),
            "availability": "full",
        })

    items.sort(key=lambda x: x["play_count"], reverse=True)
    items = items[:20]

    # Resolve the real TMDB ids by batch-fetching ProviderIds from Emby.
    # Without this, the frontend uses the Emby item id as the route
    # param when navigating to /portal/media/:type/:id and the
    # detail page either 404s or loads the WRONG title (an unrelated
    # show whose TMDB id collides with the Emby id). The bug surfaced
    # on 9-1-1 → tv/77 (Dateline), Big Bang Theory → 68088 (Gakuen
    # Handsome), etc. The fix is to ask Emby for ProviderIds.Tmdb on
    # each top item once and stamp it onto the payload.
    if emby_url and emby_key:
        emby_ids = [it["emby_item_id"] for it in items if it.get("emby_item_id")]
        if emby_ids:
            client = get_internal_client()
            try:
                res = await client.get(
                    f"{emby_url}/Items",
                    params={
                        "Ids": ",".join(emby_ids),
                        "Fields": "ProviderIds",
                        "Recursive": "true",
                    },
                    headers={"X-Emby-Token": emby_key},
                )
                if res.status_code == 200:
                    by_id = {
                        e.get("Id"): e for e in (res.json().get("Items") or [])
                    }
                    for it in items:
                        eid = it.get("emby_item_id")
                        if not eid or eid not in by_id:
                            continue
                        provs = by_id[eid].get("ProviderIds") or {}
                        tmdb = provs.get("Tmdb") or provs.get("tmdb")
                        if tmdb:
                            try:
                                it["tmdb_id"] = int(tmdb)
                            except (TypeError, ValueError):
                                pass
            except Exception as e:
                logger.warning(f"[TOP20] tmdb resolve failed: {e}")

    return {"items": items}
