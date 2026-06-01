"""List of users with their aggregated stats."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.settings import get_active_media_source
from services.portal._rank_tiers import tier_for_level
from services.portal.avatars import avatar_public_url
from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile

from ._helpers import _apply_filters
from .exclusions import _get_exclusion_filters
from .playback import _emby_user_image_url
from .users_admin import _get_hidden_users


async def get_users_stats(db: AsyncSession, page: int = 1, per_page: int = 30,
                          sort_by: str = "last_seen", sort_order: str = "desc",
                          search: str = "", show_hidden: bool = False,
                          historical_only: bool = False):
    """List all users (Emby + historical) with their stats."""
    source = await get_active_media_source(db)
    emby_users_map = {}

    if source and source.get("source") in ("emby", "jellyfin"):
        url = source.get("url", "").rstrip("/")
        api_key = source.get("api_key", "")
        if url and api_key:
            try:
                client = get_internal_client()
                res = await client.get(f"{url}/Users", headers={"X-Emby-Token": api_key}, timeout=10.0)
                if res.status_code == 200:
                    for u in res.json():
                        emby_users_map[u.get("Id", "")] = u
            except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                pass

    hidden_users = await _get_hidden_users(db)
    exc_filters = await _get_exclusion_filters(db)

    # Pull MK profile rows once so each Emby/historical row can be enriched
    # with its persistent level (and the matching tier ring) without an
    # extra round-trip per user. Users disabled or removed from Emby keep
    # whatever level they accrued on their MK profile — bronze otherwise.
    mk_profile_rows = (
        await db.execute(
            select(
                UserProfile.emby_user_id,
                UserProfile.level,
                UserProfile.avatar_url,
                UserProfile.avatar_custom_path,
            ).where(UserProfile.emby_user_id.isnot(None))
        )
    ).all()
    # Avatar resolution mirrors playback.py / sessions.py / activity.py so the
    # Users tab + merge overlay show the same photo as every other stats
    # surface: a custom MK upload wins, else the stored Emby URL, else the
    # Emby-proxied fallback (204s to a silhouette when no photo exists).
    mk_profile_map = {
        row.emby_user_id: {
            "level": row.level or 1,
            "avatar_url": (
                avatar_public_url(row.avatar_custom_path)
                if row.avatar_custom_path
                else (row.avatar_url or _emby_user_image_url(row.emby_user_id))
            ),
        }
        for row in mk_profile_rows
    }

    db_user_ids_q = _apply_filters(
        select(
            PlaybackSession.user_id,
            func.max(PlaybackSession.user_name).label("user_name"),
        ).group_by(PlaybackSession.user_id),
        exc_filters,
    )
    db_user_ids_res = await db.execute(db_user_ids_q)
    db_users = {row.user_id: row.user_name for row in db_user_ids_res}

    user_stats_rows = (
        await db.execute(
            _apply_filters(
                select(
                    PlaybackSession.user_id.label("user_id"),
                    func.count(PlaybackSession.id).label("play_count"),
                    func.sum(PlaybackSession.position_ticks).label("total_ticks"),
                ).group_by(PlaybackSession.user_id),
                exc_filters,
            )
        )
    ).all()
    user_stats_map = {
        row.user_id: {
            "play_count": row.play_count or 0,
            "total_ticks": row.total_ticks or 0,
        }
        for row in user_stats_rows
    }

    last_session_subq = _apply_filters(
        select(
            PlaybackSession.user_id.label("user_id"),
            PlaybackSession.item_name.label("item_name"),
            PlaybackSession.series_name.label("series_name"),
            PlaybackSession.item_type.label("item_type"),
            PlaybackSession.last_seen_at.label("last_seen_at"),
            PlaybackSession.device_name.label("device_name"),
            PlaybackSession.client_name.label("client_name"),
            func.row_number().over(
                partition_by=PlaybackSession.user_id,
                order_by=[PlaybackSession.last_seen_at.desc(), PlaybackSession.id.desc()],
            ).label("rn"),
        ).where(PlaybackSession.last_seen_at.isnot(None)),
        exc_filters,
    ).subquery()

    last_session_rows = (
        await db.execute(
            select(
                last_session_subq.c.user_id,
                last_session_subq.c.item_name,
                last_session_subq.c.series_name,
                last_session_subq.c.item_type,
                last_session_subq.c.last_seen_at,
                last_session_subq.c.device_name,
                last_session_subq.c.client_name,
            ).where(last_session_subq.c.rn == 1)
        )
    ).all()
    last_session_map = {row.user_id: row for row in last_session_rows}

    all_user_ids = set(emby_users_map.keys()) | set(db_users.keys())

    users_data = []
    for uid in all_user_ids:
        emby_user = emby_users_map.get(uid)
        uname = emby_user.get("Name", "") if emby_user else db_users.get(uid, uid)
        is_hidden = uid in hidden_users
        is_historical = emby_user is None

        if not show_hidden and is_hidden:
            continue

        if historical_only and not is_historical:
            continue

        if search and search.lower() not in uname.lower():
            continue

        stats = user_stats_map.get(uid, {})
        play_count = stats.get("play_count", 0)
        total_ticks = stats.get("total_ticks", 0)
        last_session = last_session_map.get(uid)

        last_seen = None
        if emby_user:
            last_seen = emby_user.get("LastActivityDate")
        if not last_seen and last_session and last_session.last_seen_at:
            last_seen = last_session.last_seen_at.isoformat()

        mk_profile = mk_profile_map.get(uid)
        level = mk_profile["level"] if mk_profile else 1
        # Emby-only users (no MK profile) still get their Emby-proxied photo,
        # matching the Top widgets / Sessions / 24h strip (no silhouette gap).
        avatar_url = mk_profile["avatar_url"] if mk_profile else _emby_user_image_url(uid)

        users_data.append({
            "user_id": uid,
            "name": uname,
            "has_image": emby_user.get("HasPrimaryImage", False) if emby_user else False,
            "avatar_url": avatar_url,
            "level": level,
            "tier": tier_for_level(level),
            "play_count": play_count,
            "total_ticks": total_ticks,
            "last_play": last_session.item_name if last_session else None,
            "last_series": last_session.series_name if last_session else None,
            "last_type": last_session.item_type if last_session else None,
            "last_seen": last_seen,
            "last_device": (
                f"{last_session.client_name or ''} - {last_session.device_name or ''}"
                if last_session and last_session.device_name
                else None
            ),
            "is_disabled": emby_user.get("Policy", {}).get("IsDisabled", False) if emby_user else False,
            "is_historical": emby_user is None,
            "is_hidden": is_hidden,
        })

    sort_key_map = {
        "name": lambda x: (x["name"] or "").lower(),
        "plays": lambda x: x["play_count"],
        "duration": lambda x: x["total_ticks"],
        "last_seen": lambda x: x["last_seen"] or "",
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["last_seen"])
    users_data.sort(key=key_fn, reverse=(sort_order == "desc"))

    total = len(users_data)
    start = (page - 1) * per_page
    page_data = users_data[start:start + per_page]

    return {"users": page_data, "total": total, "page": page, "per_page": per_page}
