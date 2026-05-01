"""'Next series to finish' carousel — series the user has already
started but hasn't fully watched yet, sorted by how few episodes
remain so the ones closest to completion land first.

Lives in its own module so the ``profile_stats_*`` split stays under
the 300-line file-size convention.
"""
import asyncio
import logging
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.playback_stats import PlaybackSession
from services.settings import (
    get_active_media_source,
    get_emby_public_url,
    get_emby_server_id,
    build_emby_deep_link,
)

from services.portal.profile_stats_recent import _find_series_emby_id
from services.portal.profile_stats_emby import _bulk_fetch_emby_info

logger = logging.getLogger("mediakeeper.portal.profile_stats")

NEXT_TO_FINISH_LIMIT = 10      # How many series to show in the carousel
CANDIDATE_SERIES_LIMIT = 40    # Upper bound on how many series to inspect


async def fetch_next_to_finish(
    db: AsyncSession, user_filter, excl_filters: list,
) -> list[dict]:
    """Series the user has watched at least one episode of but isn't
    done with yet. Each entry is sized so the frontend can reuse
    MediaCarousel + MediaCard — the green dot + "Start" button light
    up as soon as ``emby_url`` is set.

    Return shape matches ``fetch_recent_watches`` for consistency,
    plus ``remaining_count`` / ``total_count`` so the UI can render
    "Il reste N episodes".
    """
    source = await get_active_media_source(db)
    emby_url = ""
    emby_key = ""
    public_url = ""
    server_id = ""
    if source and source.get("source") in ("emby", "jellyfin"):
        emby_url = source.get("url", "").rstrip("/")
        emby_key = source.get("api_key", "")
        public_url = get_emby_public_url(source)
        server_id = await get_emby_server_id(source)

    if not emby_url or not emby_key:
        return []

    # Candidate series the user has played recently (distinct series_name).
    result = await db.execute(
        select(
            PlaybackSession.series_name,
            func.max(PlaybackSession.started_at).label("last_seen"),
        )
        .where(
            user_filter, *excl_filters,
            PlaybackSession.item_type == "Episode",
            PlaybackSession.series_name.isnot(None),
        )
        .group_by(PlaybackSession.series_name)
        .order_by(desc("last_seen"))
        .limit(CANDIDATE_SERIES_LIMIT)
    )
    rows = result.all()
    if not rows:
        return []

    # Resolve Emby user id once (same for every series) so the
    # per-series worker below doesn't re-run the same DB aggregate 40×.
    from services.portal.profile_stats_emby import resolve_emby_user_id
    emby_uid = await resolve_emby_user_id(db, user_filter)

    # Step 1: parallel-resolve every series Emby id.
    valid_rows = [r for r in rows if r.series_name]
    series_ids = await asyncio.gather(*[
        _find_series_emby_id(r.series_name, emby_url, emby_key)
        for r in valid_rows
    ])

    to_process = [
        (r, sid) for r, sid in zip(valid_rows, series_ids) if sid
    ]

    # Step 2: compute progress for every resolved series. With an
    # ``emby_uid`` available, every worker stays in the Emby-only
    # branch (no DB writes), so it's safe to gather them concurrently
    # on the same AsyncSession. Without one we fall back to the DB
    # accounting path — those must run sequentially since SQLAlchemy
    # async sessions can't handle parallel queries.
    if emby_uid:
        progress = await asyncio.gather(*[
            _series_progress(
                db, user_filter, excl_filters,
                r.series_name, sid, emby_url, emby_key, emby_uid,
            )
            for r, sid in to_process
        ])
    else:
        progress = []
        for r, sid in to_process:
            progress.append(await _series_progress(
                db, user_filter, excl_filters,
                r.series_name, sid, emby_url, emby_key, None,
            ))

    out: list[dict] = []
    for (r, series_id), (total, watched, poster_id) in zip(to_process, progress):
        series_name = r.series_name
        # "In progress" = started (≥1 watched) but not done.
        if not total or watched >= total or watched == 0:
            continue

        emby_link = build_emby_deep_link(public_url, series_id, server_id) if public_url else ""
        out.append({
            "title": series_name,
            "emby_item_id": poster_id or series_id,
            "series_emby_id": series_id,
            "poster_url": f"/api/emby/image/{poster_id or series_id}?type=Primary",
            "media_type": "tv",
            "watched_at": r.last_seen.isoformat() if r.last_seen else None,
            "watch_status": "in_progress",
            "emby_url": emby_link,
            "availability": "full",
            "total_count": total,
            "watched_count": watched,
            "remaining_count": total - watched,
        })

    # Closest-to-completion first: fewer remaining episodes ranks higher.
    out.sort(key=lambda x: (x["remaining_count"], -x["watched_count"]))
    trimmed = out[:NEXT_TO_FINISH_LIMIT]

    # Resolve TMDB ids in one bulk Emby call so card clicks open the
    # right detail page instead of falling back to the Emby id.
    series_ids = [s["series_emby_id"] for s in trimmed if s.get("series_emby_id")]
    info = await _bulk_fetch_emby_info(series_ids, emby_url, emby_key)
    for s in trimmed:
        tmdb_id = (info.get(s.get("series_emby_id")) or {}).get("tmdb_id")
        s["tmdb_id"] = tmdb_id
        s.pop("series_emby_id", None)
    return trimmed


async def _series_progress(
    db: AsyncSession, user_filter, excl_filters: list,
    series_name: str, series_emby_id: str,
    emby_url: str, emby_key: str,
    emby_uid: str | None = None,
) -> tuple[int, int, str]:
    """Return ``(total_in_emby, watched_count, poster_id)`` for the
    series. Excludes Specials + Virtual episodes. ``watched_count``
    uses Emby's per-user ``UserData.Played`` flag when available so
    "Mark as played" right-clicks are honoured (PlaybackSession
    rows alone miss those). Falls back to the play-time accounting
    when no Emby user id resolves.

    ``emby_uid`` can be passed by the caller (e.g. when iterating over
    many series for the same user) to avoid re-running the DB lookup
    for every series."""
    from services.portal.profile_stats_completion import (
        aggregate_play_signal, complete_views,
    )
    from services.portal.profile_stats_emby import resolve_emby_user_id

    if emby_uid is None:
        emby_uid = await resolve_emby_user_id(db, user_filter)
    params = {"Fields": "LocationType,ParentIndexNumber,RunTimeTicks,UserData"}
    if emby_uid:
        params["UserId"] = emby_uid
    try:
        res = await get_internal_client().get(
            f"{emby_url}/Shows/{series_emby_id}/Episodes",
            params=params,
            headers={"X-Emby-Token": emby_key},
            timeout=10.0,
        )
        if res.status_code != 200:
            return 0, 0, series_emby_id
        items = res.json().get("Items", []) or []
    except Exception:
        return 0, 0, series_emby_id

    available = [
        it for it in items
        if it.get("Id")
        and (it.get("LocationType") or "") != "Virtual"
        and it.get("ParentIndexNumber") not in (0, None)
    ]
    total = len(available)
    if total == 0:
        return 0, 0, series_emby_id

    if emby_uid:
        watched = sum(
            1 for it in available
            if (it.get("UserData") or {}).get("Played")
        )
        return total, watched, series_emby_id

    pairs = [(it.get("Id"), int(it.get("RunTimeTicks") or 0)) for it in available]
    ep_ids = [eid for eid, _ in pairs]
    rows = (await db.execute(
        select(
            PlaybackSession.item_id,
            PlaybackSession.position_ticks,
            PlaybackSession.duration_ticks,
        ).where(
            user_filter, *excl_filters,
            PlaybackSession.series_name == series_name,
            PlaybackSession.item_id.in_(ep_ids),
        )
    )).all()
    agg = aggregate_play_signal(rows)
    watched = sum(1 for eid, rt in pairs if complete_views(eid, rt, agg) >= 1)
    return total, watched, series_emby_id
