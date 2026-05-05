"""Progression-type achievement checks: leaderboard, level, tickets, watch hours, events, etc."""
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement
from models.portal.profile import UserProfile
from models.playback_stats import PlaybackSession
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.request import MediaRequest
from models.portal.ticket import Ticket
from models.portal.event import MKEvent
from models.portal.social import (
    UserList,
    UserListItem,
    PRIVACY_PUBLIC_READONLY,
    PRIVACY_COLLABORATIVE,
)
from models.portal.xp_ledger import XpLedger
from services.portal.achievements_utils import (
    update_progress,
    _coerce_utc,
    _session_duration_seconds,
)


async def check_progression(
    db: AsyncSession,
    by_type: dict[str, list[Achievement]],
    user_id: int,
    ua_map: dict,
    unlocked_ids: set[str],
    user_filter,
    excl_filters: list,
    playback_rows: list | None,
) -> list[dict]:
    """Run leaderboard/level/tickets/watch-hours/events checks. Returns newly unlocked list."""
    unlocks: list[dict] = []

    async def _apply(cond_type: str, value: int):
        if cond_type not in by_type:
            return
        for ach in by_type[cond_type]:
            if ach.id in unlocked_ids:
                continue
            r = await update_progress(db, user_id, ach.id, new_value=value, ua_map=ua_map)
            if r:
                unlocks.append(r)

    # --- Load UserProfile once for profile-based checks ---
    profile = None
    if any(k in by_type for k in (
        "profile_level", "avatar_changed", "member_years", "title_equipped",
    )):
        profile = (await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()

    # --- leaderboard_top10 / top5 / top3 / first ---
    for lb_type, max_pos in (
        ("leaderboard_top10", 10),
        ("leaderboard_top5", 5),
        ("leaderboard_top3", 3),
        ("leaderboard_first", 1),
    ):
        if lb_type in by_type:
            monthly_rank_sub = (
                select(
                    XpLedger.user_id,
                    func.extract("year", XpLedger.created_at).label("yr"),
                    func.extract("month", XpLedger.created_at).label("mo"),
                    func.sum(XpLedger.xp).label("total_xp"),
                    func.rank().over(
                        partition_by=[
                            func.extract("year", XpLedger.created_at),
                            func.extract("month", XpLedger.created_at),
                        ],
                        order_by=func.sum(XpLedger.xp).desc(),
                    ).label("pos"),
                )
                .group_by(
                    XpLedger.user_id,
                    func.extract("year", XpLedger.created_at),
                    func.extract("month", XpLedger.created_at),
                )
                .subquery()
            )
            val = (await db.execute(
                select(func.count())
                .select_from(monthly_rank_sub)
                .where(
                    monthly_rank_sub.c.user_id == user_id,
                    monthly_rank_sub.c.pos <= max_pos,
                )
            )).scalar() or 0
            await _apply(lb_type, val)

    # --- achievements_unlocked: count unlocked achievements ---
    if "achievements_unlocked" in by_type:
        await _apply("achievements_unlocked", len(unlocked_ids))

    # --- profile_level: current user level ---
    if "profile_level" in by_type and profile:
        await _apply("profile_level", profile.level or 1)

    # --- avatar_changed: user has set an avatar ---
    if "avatar_changed" in by_type and profile:
        await _apply("avatar_changed", 1 if profile.avatar_url is not None else 0)

    # --- member_years: years since account creation ---
    if "member_years" in by_type and profile and profile.created_at:
        now = datetime.now(timezone.utc)
        created = _coerce_utc(profile.created_at)
        await _apply("member_years", (now - created).days // 365 if created else 0)

    # --- title_equipped: user has selected a title ---
    if "title_equipped" in by_type and profile:
        await _apply("title_equipped", 1 if profile.selected_title is not None else 0)

    # --- tickets_created ---
    if "tickets_created" in by_type:
        val = (await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.user_id == user_id)
        )).scalar() or 0
        await _apply("tickets_created", val)

    # --- total_watch_hours: sum of playback duration in hours ---
    if "total_watch_hours" in by_type:
        rows_for_hours = playback_rows if playback_rows is not None else (
            await db.execute(
                select(PlaybackSession).where(user_filter, *excl_filters)
            )
        ).scalars().all()
        total_secs = sum(_session_duration_seconds(r) for r in rows_for_hours)
        await _apply("total_watch_hours", total_secs // 3600)

    # --- requests_approved: count approved requests ---
    if "requests_approved" in by_type:
        val = (await db.execute(
            select(func.count(MediaRequest.id))
            .where(MediaRequest.user_id == user_id, MediaRequest.status == "approved")
        )).scalar() or 0
        await _apply("requests_approved", val)

    # --- speed_runner: days where user watched 5+ distinct movies ---
    if "speed_runner" in by_type:
        speed_sub = (
            select(
                func.date(PlaybackSession.started_at).label("play_date"),
            )
            .where(
                user_filter, *excl_filters,
                PlaybackSession.item_type == "Movie",
            )
            .group_by(func.date(PlaybackSession.started_at))
            .having(func.count(distinct(PlaybackSession.item_id)) >= 5)
            .subquery()
        )
        val = (await db.execute(
            select(func.count()).select_from(speed_sub)
        )).scalar() or 0
        await _apply("speed_runner", val)

    # --- binge_session: 10+ episodes of same series in one day ---
    if "binge_session" in by_type:
        binge_sub = (
            select(
                func.date(PlaybackSession.started_at).label("play_date"),
                PlaybackSession.series_name,
            )
            .where(
                user_filter, *excl_filters,
                PlaybackSession.item_type == "Episode",
                PlaybackSession.series_name.isnot(None),
            )
            .group_by(func.date(PlaybackSession.started_at), PlaybackSession.series_name)
            .having(func.count(distinct(PlaybackSession.item_id)) >= 10)
            .subquery()
        )
        val = (await db.execute(
            select(func.count()).select_from(binge_sub)
        )).scalar() or 0
        await _apply("binge_session", val)

    # --- genre_master: genres with 100+ plays ---
    if "genre_master" in by_type:
        genre_rows_all = (await db.execute(
            select(PlaybackSession.genres)
            .where(user_filter, PlaybackSession.genres.isnot(None), *excl_filters)
        )).scalars().all()
        genre_counts: dict[str, int] = defaultdict(int)
        for g_str in genre_rows_all:
            if g_str:
                for g in g_str.split(","):
                    g = g.strip()
                    if g:
                        genre_counts[g] += 1
        await _apply("genre_master", sum(1 for cnt in genre_counts.values() if cnt >= 100))

    # --- events_created ---
    if "events_created" in by_type:
        val = (await db.execute(
            select(func.count(MKEvent.id))
            .where(MKEvent.creator_user_id == user_id)
        )).scalar() or 0
        await _apply("events_created", val)

    # --- surprise_used: count Surprise overlay openings recorded in
    # the ledger by the /api/portal/library/surprise endpoint.
    if "surprise_used" in by_type:
        val = (await db.execute(
            select(func.count(XpLedger.id))
            .where(
                XpLedger.user_id == user_id,
                XpLedger.action == "surprise_used",
            )
        )).scalar() or 0
        await _apply("surprise_used", val)

    # --- series_completed: series with episodes from 3+ different seasons ---
    if "series_completed" in by_type:
        completed_sub = (
            select(PlaybackSession.series_name)
            .where(
                user_filter, *excl_filters,
                PlaybackSession.item_type == "Episode",
                PlaybackSession.series_name.isnot(None),
                PlaybackSession.season_number.isnot(None),
            )
            .group_by(PlaybackSession.series_name)
            .having(func.count(distinct(PlaybackSession.season_number)) >= 3)
            .subquery()
        )
        val = (await db.execute(
            select(func.count()).select_from(completed_sub)
        )).scalar() or 0
        await _apply("series_completed", val)

    # --- decades_watched: distinct decades extracted from cached
    # production_year on emby_tmdb_index. Sessions whose item is not in
    # the index, or whose row has no production_year yet, are skipped.
    if "decades_watched" in by_type:
        val = (await db.execute(
            select(func.count(distinct(
                (EmbyTmdbIndex.production_year / 10) * 10
            )))
            .select_from(PlaybackSession)
            .join(
                EmbyTmdbIndex,
                PlaybackSession.item_id == EmbyTmdbIndex.emby_item_id,
            )
            .where(
                user_filter,
                EmbyTmdbIndex.production_year.isnot(None),
                *excl_filters,
            )
        )).scalar() or 0
        await _apply("decades_watched", val)

    # --- lists_public_created: count of non-deleted public/collaborative
    # lists owned by the user.
    if "lists_public_created" in by_type:
        val = (await db.execute(
            select(func.count(UserList.id)).where(
                UserList.user_id == user_id,
                UserList.is_deleted.is_(False),
                UserList.privacy.in_((PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE)),
            )
        )).scalar() or 0
        await _apply("lists_public_created", val)

    # --- lists_max_items: peak item count across the user's non-deleted
    # lists, regardless of privacy. Curation effort, not the sharing aspect.
    if "lists_max_items" in by_type:
        per_list_count = (
            select(func.count(UserListItem.id).label("cnt"))
            .select_from(UserList)
            .join(UserListItem, UserListItem.list_id == UserList.id)
            .where(
                UserList.user_id == user_id,
                UserList.is_deleted.is_(False),
            )
            .group_by(UserList.id)
            .subquery()
        )
        val = (await db.execute(
            select(func.coalesce(func.max(per_list_count.c.cnt), 0))
        )).scalar() or 0
        await _apply("lists_max_items", val)

    return unlocks
