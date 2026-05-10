"""Recent watches carousel for the profile page.

Split out of ``profile_stats_history.py`` to keep both files under 300
lines. Everything here feeds the "Recent watches" strip: filtering
loose episodes, computing watch status, and verifying the Emby poster
actually exists before we ship the row to the frontend.

Internal helpers (ratio maths, per-item/per-series lookups, series
watch-state resolver) live in ``profile_stats_recent_helpers.py``.
``_find_series_emby_id`` is re-exported from ``profile_stats_emby`` for
back-compat with ``profile_stats_next.py``.
"""
import asyncio
import logging
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from models.playback_stats import PlaybackSession
from services.settings import get_active_media_source
from services.portal._watch_threshold import WATCHED_THRESHOLD
from services.portal.profile_stats_emby import (
    _bulk_fetch_emby_info,
    _find_series_emby_id,  # noqa: F401 — re-exported for profile_stats_next
)
from services.portal.profile_stats_recent_helpers import (
    _session_ratio,
    _max_ratio_per_item,
    _max_ratio_per_series,
    _series_watch_status,  # noqa: F401 — re-exported for profile_stats_history
)

logger = logging.getLogger("mediakeeper.portal.profile_stats")

WATCHED_PROGRESS_THRESHOLD = WATCHED_THRESHOLD

# Ignore items barely started — below 10 % the user was just sampling
# the title. Prevents titles previewed then reset to 0 from clogging
# "Recent watches" as "In progress" entries.
RECENT_MIN_PROGRESS = 0.10


async def fetch_recent_watches(
    db: AsyncSession, user_filter, excl_filters: list,
) -> list[dict]:
    """Last 20 items watched, de-duplicated by title. Filters out
    non-movie/episode items, loose episodes without a series_name, and
    posters Emby can't resolve. Each entry carries a ``watch_status``
    (watched at >= 85%, else in_progress) for the UI tag."""
    recent_watches: list[dict] = []
    try:
        result = await db.execute(
            select(
                PlaybackSession.item_name, PlaybackSession.item_id,
                PlaybackSession.item_type, PlaybackSession.series_name,
                PlaybackSession.started_at,
                PlaybackSession.position_ticks, PlaybackSession.duration_ticks,
            )
            .where(user_filter, *excl_filters)
            .order_by(desc(PlaybackSession.started_at))
            .limit(120)
        )

        emby_url = emby_key = public_url = server_id = ""
        source = await get_active_media_source(db)
        if source and source.get("source") in ("emby", "jellyfin"):
            emby_url = source.get("url", "").rstrip("/")
            emby_key = source.get("api_key", "")
            from services.settings import (
                get_emby_public_url, get_emby_server_id,
            )
            public_url = get_emby_public_url(source)
            server_id = await get_emby_server_id(source)

        # First pass — build raw candidates and collect unique series
        # names so we can resolve their Emby ids concurrently.
        seen_titles: set[str] = set()
        raw: list[dict] = []
        unique_series: list[str] = []
        for r in result.all():
            if r.item_type not in ("Movie", "Episode"):
                continue
            is_episode = r.item_type == "Episode"
            if is_episode and not r.series_name:
                continue

            title = r.series_name if is_episode else r.item_name
            if title in seen_titles:
                continue
            seen_titles.add(title)
            if is_episode and r.series_name not in unique_series:
                unique_series.append(r.series_name)

            raw.append({
                "title": title,
                "is_episode": is_episode,
                "item_id": r.item_id,
                "series_name": r.series_name if is_episode else None,
                "started_at": r.started_at,
                "first_ratio": _session_ratio(r.position_ticks, r.duration_ticks),
            })
            if len(raw) >= 40:
                break

        # Parallel Emby lookups — all unique series ids in one round.
        series_id_cache: dict[str, str] = {}
        if unique_series and emby_url and emby_key:
            ids = await asyncio.gather(*[
                _find_series_emby_id(sn, emby_url, emby_key)
                for sn in unique_series
            ])
            series_id_cache = {sn: (sid or "") for sn, sid in zip(unique_series, ids)}

        candidates: list[dict] = []
        for row in raw:
            poster_id = row["item_id"]
            media_type = "tv" if row["is_episode"] else "movie"
            if row["is_episode"] and emby_url and emby_key:
                cached = series_id_cache.get(row["series_name"], "")
                if not cached:
                    # We couldn't resolve the series — the episode still
                    # image is unreliable (and often empty), so drop the
                    # row rather than ship a broken poster.
                    continue
                poster_id = cached
            candidates.append({
                "title": row["title"],
                "emby_item_id": poster_id,
                "media_type": media_type,
                "series_name": row["series_name"],
                "item_id": row["item_id"],
                "started_at": row["started_at"],
                "first_ratio": row["first_ratio"],
            })

        # Bulk-fetch image availability + TMDB id in one Emby call.
        # ``tmdb_id`` is what MediaCard clicks route on, and
        # ``has_image`` lets us skip posterless rows (intros, theme
        # music indexed as Episode, custom rips without metadata).
        poster_ids = [c["emby_item_id"] for c in candidates if c["emby_item_id"]]
        emby_info = await _bulk_fetch_emby_info(poster_ids, emby_url, emby_key)

        # Bulk-fetch UserData (per-user Played flag) for movies — this
        # is the authoritative "watched" signal: it covers both real
        # plays and Mark-as-played actions, and survives library re-
        # scans that change item ids in the playback table.
        from services.portal.profile_stats_emby import resolve_emby_user_id
        emby_uid = await resolve_emby_user_id(db, user_filter) if emby_url else None
        movie_ids_for_userdata = [
            c["emby_item_id"] for c in candidates
            if c["media_type"] == "movie" and c["emby_item_id"]
        ]
        movie_played: dict[str, bool] = {}
        if movie_ids_for_userdata and emby_uid and emby_url:
            try:
                res = await get_internal_client().get(
                    f"{emby_url}/Users/{emby_uid}/Items",
                    params={"Ids": ",".join(movie_ids_for_userdata), "Fields": "UserData"},
                    headers={"X-Emby-Token": emby_key}, timeout=10.0,
                )
                if res.status_code == 200:
                    for item in res.json().get("Items", []):
                        movie_played[item.get("Id", "")] = bool((item.get("UserData") or {}).get("Played"))
            except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                pass

        # Aggregate max progress per item_id so movies with multiple
        # sessions report the best coverage, not whichever row happened
        # to land in the 120-row slice.
        item_ids = [c["item_id"] for c in candidates]
        max_ratio_by_item = await _max_ratio_per_item(db, user_filter, excl_filters, item_ids)

        # Best coverage per series (max ratio across every episode the
        # user has played) so we can drop series the user only peeked
        # at before resetting playback.
        series_names = [
            c["series_name"] for c in candidates
            if c["media_type"] == "tv" and c["series_name"]
        ]
        max_ratio_by_series = await _max_ratio_per_series(
            db, user_filter, excl_filters, series_names,
        )

        # Resolve watch status for every unique TV series. With an
        # ``emby_uid`` available we can fire the Emby /Episodes calls
        # concurrently (no DB writes on the fast path); otherwise the
        # fallback path touches the async session so we iterate
        # sequentially to avoid a concurrent-query error.
        series_status_cache: dict[str, str] = {}
        unique_tv = []
        for c in candidates:
            if c["media_type"] == "tv" and c["series_name"] and c["series_name"] not in series_status_cache:
                series_status_cache[c["series_name"]] = ""  # placeholder
                unique_tv.append((c["series_name"], c["emby_item_id"]))
        if unique_tv:
            if emby_uid:
                statuses = await asyncio.gather(*[
                    _series_watch_status(
                        db, user_filter, excl_filters, sname, sid, emby_url, emby_key, emby_uid,
                    )
                    for sname, sid in unique_tv
                ])
            else:
                statuses = []
                for sname, sid in unique_tv:
                    statuses.append(await _series_watch_status(
                        db, user_filter, excl_filters, sname, sid, emby_url, emby_key, None,
                    ))
            for (sname, _sid), st in zip(unique_tv, statuses):
                series_status_cache[sname] = st

        for c in candidates:
            info = emby_info.get(c["emby_item_id"]) or {}
            tmdb_id = info.get("tmdb_id")
            # Strict cleanup: items with no TMDB match (intros, theme
            # music re-tagged as Episode by Emby, custom rips without
            # provider ids) and items with no Primary image are not
            # surfaced — they'd render as broken posters and link
            # nowhere useful.
            if not tmdb_id:
                continue
            if not info.get("has_image", False):
                continue
            if c["media_type"] == "movie":
                # Drop movies the user only sampled (< 10 %) when the
                # session has a real ratio to test against. Legacy
                # rows (no ``duration_ticks``) skip this filter and
                # use Emby UserData.Played instead.
                ratio = max(max_ratio_by_item.get(c["item_id"], 0.0), c["first_ratio"] or 0.0)
                if ratio > 0 and ratio < RECENT_MIN_PROGRESS:
                    continue
                if c["emby_item_id"] in movie_played:
                    status = "watched" if movie_played[c["emby_item_id"]] else "in_progress"
                else:
                    status = "watched" if ratio >= WATCHED_PROGRESS_THRESHOLD else "in_progress"
            else:
                best_ratio = max(
                    max_ratio_by_series.get(c["series_name"], 0.0),
                    c["first_ratio"] or 0.0,
                )
                if best_ratio > 0 and best_ratio < RECENT_MIN_PROGRESS:
                    continue
                status = series_status_cache.get(c["series_name"], "in_progress")
            # Every recent-watch item is by definition in Emby, so we
            # can ship the deep-link straight away — MediaCard renders
            # the green dot + "Play" CTA as soon as emby_url is set.
            from services.settings import build_emby_deep_link
            emby_link = (
                build_emby_deep_link(public_url, c["emby_item_id"], server_id)
                if public_url and c["emby_item_id"] else ""
            )
            recent_watches.append({
                "title": c["title"],
                "emby_item_id": c["emby_item_id"],
                "tmdb_id": tmdb_id,
                "poster_url": f"/api/emby/image/{c['emby_item_id']}?type=Primary" if c["emby_item_id"] else "",
                "media_type": c["media_type"],
                "watched_at": c["started_at"].isoformat() if c["started_at"] else None,
                "watch_status": status,
                "emby_url": emby_link,
                "availability": "full",
            })
            if len(recent_watches) >= 20:
                break
    except Exception as e:
        logger.debug(f"[PROFILE] recent watches error: {e}")
    return recent_watches
