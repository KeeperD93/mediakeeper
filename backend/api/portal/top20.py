"""Top 20 most played media this month — same logic as stats_aggregator.

The URL route, the function name and the tags are intentionally kept
as ``top20`` so the frontend and any external consumers that already
hit ``/api/portal/top20`` keep working unchanged. Only the file and
the logger scope were renamed to reflect the real rank depth (20).
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.http_client import get_internal_client
from models.user import User
from models.portal.profile import UserProfile
from models.playback_stats import PlaybackSession
from api.portal.deps import get_current_profile
from services.portal._watch_threshold import watched_session_filter
from services.tmdb import get_meta_cached
from services.settings import (
    get_active_media_source,
    get_emby_public_url,
    get_emby_server_id,
    build_emby_deep_link,
)

router = APIRouter(prefix="/top20", tags=["portal-top20"])
logger = logging.getLogger("mediakeeper.portal.top20")

_series_id_cache: dict[str, str] = {}
# Cap the name→id memo so a library with many distinct series can't grow it
# without bound over the process lifetime; drop it wholesale when full.
_SERIES_ID_CACHE_MAX = 2000

# The Top 20 is identical for every viewer (global "most played this month"),
# so cache the whole payload briefly: repeated loads then skip the playback
# aggregation + Emby/TMDB round-trips instead of recomputing per request.
_TOP20_TTL_SECONDS = 600
_top20_result_cache: dict[str, object] = {"payload": None, "at": None}


async def _enrich_top20_meta(items: list[dict], db: AsyncSession) -> None:
    """Stamp runtime + year + TMDB rating on Top 20 items in-place.

    The lookup is cheap thanks to the TMDB meta cache (24h TTL). Items
    without a tmdb_id stay untouched, and per-item TMDB failures are
    logged but never propagated — a single hiccup must not kill the
    whole payload.
    """
    for it in items:
        tid = it.get("tmdb_id")
        mtype = it.get("media_type")
        if not tid or not mtype:
            continue
        try:
            meta = await get_meta_cached(int(tid), mtype, db)
        except Exception as e:
            logger.warning(f"[TOP20] meta enrich failed for {mtype}/{tid}: {e}")
            continue
        if meta.get("runtime"):
            it["runtime"] = meta["runtime"]
        if meta.get("year"):
            it["year"] = meta["year"]
        if meta.get("vote"):
            it["vote"] = meta["vote"]


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
                if len(_series_id_cache) >= _SERIES_ID_CACHE_MAX:
                    _series_id_cache.clear()
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
    cached_at = _top20_result_cache["at"]
    if (
        _top20_result_cache["payload"] is not None
        and cached_at is not None
        and (now - cached_at).total_seconds() < _TOP20_TTL_SECONDS
    ):
        return _top20_result_cache["payload"]

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

    # Top movies — count = distinct viewers (1 user re-watching the
    # same film stays at 1). Sub-85% sessions are dropped so a movie
    # someone sampled for 5 minutes doesn't crowd the chart.
    watched = watched_session_filter()
    movies_q = await db.execute(
        select(
            PlaybackSession.item_name,
            PlaybackSession.item_id,
            func.count(distinct(PlaybackSession.user_id)).label("play_count"),
        )
        .where(
            PlaybackSession.item_type == "Movie",
            PlaybackSession.started_at >= month_start,
            watched,
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

    # Top series — count = distinct viewers per series. Without the
    # DISTINCT, a single user binging 100 episodes would push the show
    # past every movie in the chart (which always count 1 per user).
    # Episodes are filtered to the watch threshold first so a quick
    # peek at the first 5 minutes doesn't qualify the series.
    series_q = await db.execute(
        select(
            PlaybackSession.series_name,
            func.count(distinct(PlaybackSession.user_id)).label("play_count"),
        )
        .where(
            PlaybackSession.item_type == "Episode",
            PlaybackSession.series_name.isnot(None),
            PlaybackSession.started_at >= month_start,
            watched,
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

    # Backfill runtime + year so MediaCard can render the poster meta
    # line without a second round-trip on the client. Missing values
    # stay absent and the frontend elides the separator instead of
    # showing an empty " · ".
    await _enrich_top20_meta(items, db)

    result = {"items": items}
    _top20_result_cache["payload"] = result
    _top20_result_cache["at"] = now
    return result
