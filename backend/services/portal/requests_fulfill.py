"""Mark open media requests ``available`` once Emby holds what they asked for.

Runs as its own scheduled task so it works whether or not Discord
notifications are configured. A movie is served as soon as the Emby <-> TMDB
index holds it; a series once every requested episode that has already aired
is in Emby, with the airing rules of the portal availability pill.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import Row, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from constants.notifications import NOTIF_REQUEST_AVAILABLE
from constants.requests import OPEN_REQUEST_STATUSES, REQUEST_AVAILABLE
from constants.tmdb_media import TMDB_MEDIA_TV
from constants.tmdb_status import TMDB_TERMINAL_STATUSES
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.request import MediaRequest
from services.portal import notifications as notif_svc
from services.portal.achievements import safe_check_all_achievements
from services.watchlist_scanner._emby import _get_emby_episodes
from services.watchlist_scanner._tmdb import _tmdb_season, _tmdb_series
from services.watchlist_tracking import get_ignored

logger = logging.getLogger("mediakeeper.portal.requests")


async def fulfill_open_requests(db: AsyncSession) -> int:
    """Flip every open request whose content is in Emby, notify each requester
    and re-check their trophies. Returns the number of requests flipped."""
    # Plain rows, not ORM objects: the per-request commits and rollbacks would expire them.
    rows = (await db.execute(
        select(
            MediaRequest.id, MediaRequest.user_id, MediaRequest.tmdb_id,
            MediaRequest.media_type, MediaRequest.title, MediaRequest.poster_url,
            MediaRequest.requested_seasons,
        )
        .where(MediaRequest.status.in_(OPEN_REQUEST_STATUSES))
        .order_by(MediaRequest.created_at, MediaRequest.id)
    )).all()
    if not rows:
        return 0

    # A title can have several index rows (re-import leaves an orphan behind).
    emby_ids: dict[tuple[int, str], list[str]] = {}
    for tmdb_id, media_type, emby_item_id in await db.execute(
        select(EmbyTmdbIndex.tmdb_id, EmbyTmdbIndex.media_type, EmbyTmdbIndex.emby_item_id)
        .where(EmbyTmdbIndex.tmdb_id.in_([r.tmdb_id for r in rows]))
    ):
        emby_ids.setdefault((tmdb_id, media_type), []).append(emby_item_id)

    ignored: set[str] | None = None
    requesters: set[int] = set()
    flipped = 0
    for req in rows:
        series_ids = emby_ids.get((req.tmdb_id, req.media_type))
        if not series_ids:
            continue
        try:
            if req.media_type == TMDB_MEDIA_TV:
                if ignored is None:
                    ignored = set(await get_ignored(db))
                if not await _series_request_served(db, req, series_ids, ignored):
                    continue
            if await _mark_available(db, req):
                flipped += 1
                if req.user_id is not None:
                    requesters.add(req.user_id)
        except Exception:
            # One failing request must not block the others; it is retried next run.
            await db.rollback()
            logger.exception("[REQUESTS] fulfilment failed for request_id=%s", req.id)

    for user_id in requesters:
        await safe_check_all_achievements(
            db, user_id=user_id, user_name=None, source="request_status_change",
        )
    if flipped:
        logger.info("[REQUESTS] %s request(s) marked available", flipped)
    return flipped


async def _mark_available(db: AsyncSession, req: Row) -> bool:
    """Flip one request and add the bell notification in the same commit.

    The status guard keeps the flip idempotent and leaves alone a request an
    admin moved meanwhile."""
    result = await db.execute(
        update(MediaRequest)
        .where(MediaRequest.id == req.id, MediaRequest.status.in_(OPEN_REQUEST_STATUSES))
        .values(status=REQUEST_AVAILABLE, available_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session="fetch")
    )
    if not result.rowcount:
        return False
    # A GDPR-purged requester (user_id NULL) has no bell to notify.
    if req.user_id is not None:
        await notif_svc.create(db, req.user_id, NOTIF_REQUEST_AVAILABLE, {
            "tmdb_id": req.tmdb_id,
            "media_type": req.media_type,
            "title": req.title,
            "poster_url": req.poster_url,
            "request_id": req.id,
        })
    await db.commit()
    return True


async def _series_request_served(
    db: AsyncSession, req: Row, series_ids: list[str], ignored: set[str],
) -> bool:
    """True when Emby holds every requested episode that has already aired.

    Every episode of an ended series counts, otherwise only the aired ones;
    episodes ignored in the Watchlist count as present. A request with nothing
    aired yet stays open."""
    wanted = _requested_episodes(req.requested_seasons)
    series = await _tmdb_series(db, req.tmdb_id)
    if not series:
        return False
    ended = (series.get("status") or "").lower() in TMDB_TERMINAL_STATUSES
    today = date.today().isoformat()
    # A whole-series request covers every regular season (specials excluded).
    seasons = wanted if wanted is not None else {
        s["season_number"]: None for s in series.get("seasons", []) if s.get("season_number")
    }

    required: set[tuple[int, int]] = set()
    for season_number, episodes in seasons.items():
        season = await _tmdb_season(db, req.tmdb_id, season_number)
        if not season:
            return False
        for ep in season.get("episodes", []):
            number = ep.get("episode_number")
            if number is None or (episodes is not None and number not in episodes):
                continue
            air_date = ep.get("air_date") or ""
            if not ended and not (air_date and air_date <= today):
                continue
            if f"{req.tmdb_id}_s{season_number}_e{number}" not in ignored:
                required.add((season_number, number))
    if not required:
        return False

    present: set[tuple[int, int]] = set()
    for series_id in series_ids:
        present |= (await _get_emby_episodes(db, series_id, present_only=True)).keys()
    return required <= present


def _requested_episodes(raw: list | None) -> dict[int, set[int] | None] | None:
    """Map ``{season: episodes}`` from a request, ``None`` episodes meaning the
    whole season. ``None`` overall means the whole series.

    Reads the request modal's ``{"season": N, "episodes": "all" | [n, ...]}``
    entries and bare season numbers from older rows; an unreadable payload
    falls back to the whole series, the strictest reading."""
    seasons: dict[int, set[int] | None] = {}
    for entry in raw or []:
        if isinstance(entry, int):
            seasons[entry] = None
        elif isinstance(entry, dict) and isinstance(entry.get("season"), int):
            episodes = entry.get("episodes")
            seasons[entry["season"]] = (
                {n for n in episodes if isinstance(n, int)} if isinstance(episodes, list) else None
            )
    return seasons or None
