"""Internal helpers for ``profile_stats_recent.py``.

Pure utilities (progress ratio math, per-item/per-series max-ratio
lookups, series watched-state resolution). Kept out of the main
recent-watches pipeline so that file stays a readable top-to-bottom
read of the user-facing "recent plays" query.
"""
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.playback_stats import PlaybackSession

logger = logging.getLogger("mediakeeper.portal.profile_stats")


def _session_ratio(position_ticks: int | None, duration_ticks: int | None) -> float:
    """Fraction of the media that was played.

    Live-capture rows have a real ``duration_ticks`` so the ratio is
    exact. Legacy rows imported from Emby's Playback Reporting plugin
    store ``duration_ticks=0`` (it only logs play time, not runtime);
    for those we fall back to assuming a full viewing when the user
    watched for at least a minute — shorter than that is a sample and
    gets filtered like any other short play.
    """
    if not duration_ticks or duration_ticks <= 0:
        # 1 minute in Emby ticks. Anything shorter was a quick sample.
        if not position_ticks or position_ticks < 600_000_000:
            return 0.0
        return 1.0
    if not position_ticks:
        return 0.0
    return min(max(position_ticks / duration_ticks, 0.0), 1.5)


async def _max_ratio_per_item(
    db: AsyncSession, user_filter, excl_filters: list, item_ids: list[str],
) -> dict[str, float]:
    if not item_ids:
        return {}
    result = await db.execute(
        select(
            PlaybackSession.item_id,
            func.max(PlaybackSession.position_ticks).label("max_pos"),
            func.max(PlaybackSession.duration_ticks).label("max_dur"),
        )
        .where(
            user_filter, *excl_filters,
            PlaybackSession.item_id.in_(item_ids),
        )
        .group_by(PlaybackSession.item_id)
    )
    out: dict[str, float] = {}
    for row in result.all():
        out[row.item_id] = _session_ratio(row.max_pos, row.max_dur)
    return out


async def _max_ratio_per_series(
    db: AsyncSession, user_filter, excl_filters: list, series_names: list[str],
) -> dict[str, float]:
    """Best per-episode ratio ever recorded for each series — used to
    drop series the user only peeked at."""
    if not series_names:
        return {}
    result = await db.execute(
        select(
            PlaybackSession.series_name,
            PlaybackSession.position_ticks,
            PlaybackSession.duration_ticks,
        )
        .where(
            user_filter, *excl_filters,
            PlaybackSession.series_name.in_(series_names),
        )
    )
    out: dict[str, float] = {}
    for row in result.all():
        r = _session_ratio(row.position_ticks, row.duration_ticks)
        if r > out.get(row.series_name, 0.0):
            out[row.series_name] = r
    return out


async def _series_watch_status(
    db: AsyncSession, user_filter, excl_filters: list,
    series_name: str, series_emby_id: str,
    emby_url: str, emby_key: str,
    emby_uid: str | None = None,
) -> str:
    """A series is 'watched' once every available non-special episode
    is marked Played in Emby for this user. We trust Emby's per-user
    UserData.Played as the authoritative signal — it reflects both
    real plays and "Mark as played" right-clicks the user did
    directly in Emby, which our PlaybackSession table can't see.
    Falls back to the play-time accounting when no Emby user id can
    be resolved (older accounts without playback rows).

    ``emby_uid`` can be passed by callers iterating over many series
    to skip the per-call DB lookup and let the function run safely
    concurrently on the same AsyncSession."""
    from services.portal.profile_stats_completion import (
        aggregate_play_signal, complete_views,
    )
    from services.portal.profile_stats_emby import resolve_emby_user_id

    if not series_emby_id or not emby_url or not emby_key:
        return "in_progress"

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
            return "in_progress"
        items = res.json().get("Items", []) or []
    except Exception:
        return "in_progress"

    available = [
        it for it in items
        if it.get("Id")
        and (it.get("LocationType") or "") != "Virtual"
        and it.get("ParentIndexNumber") not in (0, None)
    ]
    if not available:
        return "in_progress"

    if emby_uid:
        for it in available:
            if not (it.get("UserData") or {}).get("Played"):
                return "in_progress"
        return "watched"

    # Fallback path: no Emby user resolved → use playback rows.
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
    for eid, rt in pairs:
        if complete_views(eid, rt, agg) < 1:
            return "in_progress"
    return "watched"
