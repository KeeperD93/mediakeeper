"""Availability check: batch lookup of TMDB IDs against Emby index."""
import asyncio
import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.http_client import get_internal_client
from core.rate_limit import limiter, portal_user_or_ip_key
from models.user import User
from models.portal.profile import UserProfile
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from api.portal.deps import get_current_profile
from services.settings import (
    get_active_media_source,
    get_emby_public_url,
    get_emby_server_id,
    build_emby_deep_link,
)
# Reuse the watchlist ("suivi") module's Emby + TMDB helpers so our
# notion of "complete series" matches what the Watchlist scanner
# already shows the user. Both helpers are cached (6h TTL for TMDB).
from services.watchlist_scanner._emby import _get_emby_episodes
from services.watchlist_scanner._tmdb import _tmdb_series, _tmdb_season
# Ignored episodes in the Watchlist module must also be ignored here:
# if the user has marked an episode as "don't care" (e.g. a special),
# the Portal UI shouldn't flag the series as incomplete nor let
# anyone re-request that episode.
from services.watchlist_tracking import get_ignored


def _ignored_key(tmdb_id: int, season: int, episode: int) -> str:
    """Same shape the Watchlist UI stores: ``{tmdb}_s{N}_e{M}``."""
    return f"{tmdb_id}_s{season}_e{episode}"

router = APIRouter(prefix="/availability", tags=["portal-availability"])
logger = logging.getLogger("mediakeeper.portal.availability")


class AvailabilityItem(BaseModel):
    """Single entry in the batch availability query.

    Pydantic v2 coerces a numeric string into an ``int`` automatically
    (matches the historical frontend payload that occasionally sent
    ``tmdb_id`` as a string). Non-numeric input returns a clean 422
    instead of crashing on the asyncpg parameter binding — the
    underlying ``EmbyTmdbIndex.tmdb_id`` is a strict ``Integer`` column
    that refuses anything else.
    """

    model_config = ConfigDict(extra="forbid")

    tmdb_id: int
    media_type: Literal["movie", "tv"] = "movie"


class AvailabilityQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AvailabilityItem]


@router.post("")
# 120/minute (vs the historical 30/minute) — the endpoint is cheap
# (index lookup + parallel TV completeness checks), batched from the
# frontend, and called in burst on the Home (13 carousels). The
# previous limit saturated under normal use and stacked rate-limit
# notifications.
@limiter.limit("120/minute", key_func=portal_user_or_ip_key)
async def check_availability(
    query: AvailabilityQuery,
    request: Request,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch check availability for a list of {tmdb_id, media_type}.
    Returns {tmdb_id: {availability, emby_item_id, emby_url}}.
    """
    if not query.items:
        return {"results": {}}

    tmdb_ids = [it.tmdb_id for it in query.items if it.tmdb_id]
    if not tmdb_ids:
        return {"results": {}}

    # Fetch all matching index entries, freshest first so the deep link
    # below points at the most recently upserted ItemId (orphans of a
    # past re-import sort last and won't be picked).
    result = await db.execute(
        select(EmbyTmdbIndex)
        .where(EmbyTmdbIndex.tmdb_id.in_(tmdb_ids))
        .order_by(EmbyTmdbIndex.updated_at.desc())
    )
    entries = result.scalars().all()

    # A single tmdb_id can have multiple index rows when an Emby item is
    # deleted and re-imported (new ItemId, old row stays until the next
    # sync). We keep the full list here so completeness checks can union
    # episodes across all instances; the deep link uses the first one.
    index_map: dict[int, list[EmbyTmdbIndex]] = {}
    for e in entries:
        index_map.setdefault(e.tmdb_id, []).append(e)

    # public_url is used to build user-facing "Watch" deep links (HTTPS
    # preferred, falls back to internal URL when not configured). The
    # internal URL is no longer needed here — the completeness check
    # delegates to the watchlist scanner, which reads the Emby config
    # on its own.
    source = await get_active_media_source(db)
    emby_url = get_emby_public_url(source) if source else ""
    server_id = await get_emby_server_id(source) if source else ""
    ignored_set = set(await get_ignored(db))

    # TV completeness checks are independent — run them in parallel so
    # a page with ~20 series doesn't serialise 20 × (Emby + TMDB) calls.
    # Movies and non-indexed items skip the check entirely.
    tv_jobs: dict[int, asyncio.Task] = {}
    for it in query.items:
        tmdb_id = it.tmdb_id
        media_type = it.media_type
        entries_for_tmdb = index_map.get(tmdb_id)
        if entries_for_tmdb and media_type == "tv":
            emby_ids = [e.emby_item_id for e in entries_for_tmdb]
            tv_jobs[tmdb_id] = asyncio.create_task(
                _check_series_completeness(db, emby_ids, tmdb_id, ignored_set)
            )

    tv_status: dict[int, str] = {}
    if tv_jobs:
        await asyncio.gather(*tv_jobs.values(), return_exceptions=True)
        for tid, task in tv_jobs.items():
            try:
                tv_status[tid] = task.result()
            except Exception as e:
                logger.warning("[AVAILABILITY] tv completeness %s: %s", tid, e)
                tv_status[tid] = "full"

    results = {}
    for it in query.items:
        tmdb_id = it.tmdb_id
        media_type = it.media_type
        if not tmdb_id:
            continue

        entries_for_tmdb = index_map.get(tmdb_id)
        if entries_for_tmdb:
            entry = entries_for_tmdb[0]
            avail = tv_status.get(tmdb_id, "full") if media_type == "tv" else "full"
            # User-facing deep link uses the public URL + serverId.
            # Emby 4.9+ requires the serverId query param to render the
            # item page; without it the SPA loads but stays blank.
            emby_link = build_emby_deep_link(emby_url, entry.emby_item_id, server_id)
            results[str(tmdb_id)] = {
                "availability": avail,
                "emby_item_id": entry.emby_item_id,
                "emby_url": emby_link,
            }
        else:
            # Explicit null distinguishes "not indexed yet" from "indexed
            # with no availability" — the frontend cache flags null as
            # ``_empty`` so MediaCard falls back to the inline hint
            # stamped by /library/recent while EmbyTmdbIndex catches up
            # on freshly added Emby items. Returning an all-null object
            # previously looked like a real hit and silently erased the
            # "Dispo" badge ~0.5 s after page load.
            results[str(tmdb_id)] = None

    return {"results": results}


async def _check_series_completeness(
    db: AsyncSession,
    emby_series_ids: list[str],
    tmdb_id: int,
    ignored_set: set[str] | None = None,
) -> str:
    """
    Same model as the Watchlist ("suivi") scanner: a series is
    "partial" if any TMDB episode that has ALREADY AIRED is not yet
    in Emby. Upcoming episodes don't count as missing (they'd wrongly
    mark every ongoing show as partial).

    Episodes the user has ignored in the Watchlist are treated as if
    they were present — they don't trigger partial status. This keeps
    the two modules consistent (a series considered "done" in Suivi
    can't suddenly look incomplete in Portal).

    For ended / canceled series we walk per-season anyway so that
    ignored episodes can be excluded from the count.

    ``emby_series_ids`` is a list because a single TMDB id can have
    multiple index rows after a re-import (orphan + new). We union
    their episode sets so a stale orphan with 0 episodes can't drag
    the status to "partial" on its own.
    """
    td = await _tmdb_series(db, tmdb_id)
    if not td:
        return "full"

    emby_set: set[tuple[int, int]] = set()
    if emby_series_ids:
        ep_maps = await asyncio.gather(
            *[_get_emby_episodes(db, sid) for sid in emby_series_ids],
            return_exceptions=True,
        )
        for m in ep_maps:
            if isinstance(m, dict):
                emby_set |= m.keys()
    ignored_set = ignored_set or set()
    today = date.today().isoformat()
    status = (td.get("status") or "").lower()
    is_ended = status in ("ended", "canceled")

    for si in td.get("seasons", []):
        sn = si.get("season_number", 0)
        if sn == 0:
            continue
        sd = await _tmdb_season(db, tmdb_id, sn)
        if not sd:
            continue
        for ep in sd.get("episodes", []):
            en = ep.get("episode_number")
            if en is None:
                continue
            if _ignored_key(tmdb_id, sn, en) in ignored_set:
                continue
            if (sn, en) in emby_set:
                continue
            # Past this point the episode is missing from Emby AND
            # isn't on the user's ignore list. For ongoing shows we
            # still honour the air-date gate so upcoming episodes
            # don't look like gaps.
            if is_ended:
                return "partial"
            air = ep.get("air_date", "")
            if air and air <= today:
                return "partial"
    return "full"


@router.get("/tv/{tmdb_id}/episodes")
async def tv_available_episodes(
    tmdb_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Per-season / per-episode availability lookup for the RequestModal.

    Returns three buckets per season:
      - ``available``: episodes already in the Emby library
      - ``ignored``:   episodes the admin has ignored in the Watchlist
                       module (won't be downloaded, must stay uncheckable
                       so the user can't re-request them). The list comes
                       from the Suivi ignore store keyed ``{tmdb}_s{N}_e{M}``.

    Shape: ``{ in_emby, seasons: { "1": { available: [...], ignored: [...] } } }``.
    """
    source = await get_active_media_source(db)
    if not source:
        return {"in_emby": False, "seasons": {}}

    emby_url = (source.get("url") or "").rstrip("/")
    api_key = source.get("api_key") or ""
    if not emby_url or not api_key:
        return {"in_emby": False, "seasons": {}}

    # All matching index rows: a TMDB id can map to multiple Emby items
    # if a title was re-imported (orphan + new). We query all instances
    # and union their episode lists below so a stale orphan with 0
    # episodes can't make a fully-stocked series look incomplete.
    result = await db.execute(
        select(EmbyTmdbIndex).where(EmbyTmdbIndex.tmdb_id == tmdb_id)
    )
    entries = result.scalars().all()

    ignored_set = set(await get_ignored(db))
    # Collect ignored episodes belonging to this series up-front so we
    # can report them even when the series isn't indexed in Emby yet
    # (e.g. a brand-new season is released and nothing is scanned yet).
    ignored_by_season: dict[int, list[int]] = {}
    prefix = f"{tmdb_id}_s"
    for key in ignored_set:
        if not key.startswith(prefix):
            continue
        try:
            body = key[len(prefix):]  # "{N}_e{M}"
            s_part, e_part = body.split("_e", 1)
            s_num = int(s_part)
            e_num = int(e_part)
        except Exception:  # noqa: S112 -- intentional best-effort iteration, skip individual failure
            continue
        ignored_by_season.setdefault(s_num, []).append(e_num)

    if not entries:
        # Series not in Emby at all but ignored metadata may still apply
        # (e.g. user ignored a special from TMDB without ever owning it).
        seasons_out = {
            str(sn): {"available": [], "ignored": sorted(set(eps))}
            for sn, eps in ignored_by_season.items()
        }
        return {"in_emby": False, "seasons": seasons_out}

    client = get_internal_client()

    async def _fetch_episodes(emby_id: str) -> list:
        try:
            res = await client.get(
                f"{emby_url}/Shows/{emby_id}/Episodes",
                params={"Fields": "LocationType"},
                headers={"X-Emby-Token": api_key},
                timeout=15.0,
            )
            if res.status_code != 200:
                return []
            return res.json().get("Items", []) or []
        except Exception as e:  # noqa: BLE001 -- best-effort per-shard fetch
            logger.warning(
                "[AVAILABILITY] episode fetch failed for %s: %s", emby_id, e
            )
            return []

    fetched = await asyncio.gather(*[_fetch_episodes(e.emby_item_id) for e in entries])
    items = [ep for batch in fetched for ep in batch]

    # Bucket real (non-virtual) episodes by season number. Virtual
    # episodes in Emby are placeholders for expected but not yet
    # downloaded content — treat them as NOT available.
    seasons: dict[str, dict] = {}
    for ep in items:
        s_num = ep.get("ParentIndexNumber")
        e_num = ep.get("IndexNumber")
        if s_num is None or e_num is None:
            continue
        loc = ep.get("LocationType") or ""
        key = str(s_num)
        bucket = seasons.setdefault(key, {"available": [], "ignored": []})
        if loc != "Virtual":
            bucket["available"].append(e_num)

    # Merge ignored lists in — make sure every season the user has
    # marked (even if not returned by Emby yet) shows up.
    for s_num, eps in ignored_by_season.items():
        bucket = seasons.setdefault(str(s_num), {"available": [], "ignored": []})
        bucket["ignored"] = sorted(set(eps))

    for key, bucket in seasons.items():
        bucket["available"] = sorted(set(bucket.get("available", [])))
        bucket["ignored"] = sorted(set(bucket.get("ignored", [])))

    return {"in_emby": True, "seasons": seasons}
