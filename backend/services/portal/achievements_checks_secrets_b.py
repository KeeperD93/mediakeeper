"""Secret achievement checks — part B (time-window, bilingual, ultra, zapper, ultimate, placeholders)."""
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy import select, func, distinct, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.achievement import Achievement
from models.playback_stats import PlaybackSession
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from services.portal.achievements_utils import (
    update_progress,
    _coerce_utc,
    _session_duration_seconds,
)
from services.portal.iso_lang_map import audio_matches_original
from services.portal.playback_overlap import (
    find_concurrent_other_user_session,
    has_distinct_user_universe,
    has_same_item_other_user_overlap,
)
from services.portal.playback_algorithms import (
    has_24h_in_48h_window,
    has_12_consecutive_top1_months,
    has_all_night_chain,
    is_first_viewer_of_fresh_content,
)


async def check_secrets_b(
    db: AsyncSession,
    by_type: dict[str, list[Achievement]],
    user_id: int,
    ua_map: dict,
    unlocked_ids: set[str],
    user_filter,
    excl_filters: list,
    playback_rows: list | None,
    all_achs: list,
) -> list[dict]:
    """Run second half of secret checks + ultimate_collector. Returns newly unlocked list."""
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

    # --- secret_countdown: play started between 23:59 and 00:01 ---
    if "secret_countdown" in by_type:
        val = (await db.execute(
            select(func.count(PlaybackSession.id))
            .where(
                user_filter, *excl_filters,
                or_(
                    and_(
                        func.extract("hour", PlaybackSession.started_at) == 23,
                        func.extract("minute", PlaybackSession.started_at) == 59,
                    ),
                    and_(
                        func.extract("hour", PlaybackSession.started_at) == 0,
                        func.extract("minute", PlaybackSession.started_at) <= 1,
                    ),
                ),
            )
        )).scalar() or 0
        await _apply("secret_countdown", 1 if val > 0 else 0)

    # --- secret_sunday: 6h+ watched on a single Sunday ---
    if "secret_sunday" in by_type:
        rows_for_sunday = playback_rows if playback_rows is not None else (
            await db.execute(
                select(PlaybackSession).where(user_filter, *excl_filters)
            )
        ).scalars().all()
        sunday_hours: dict[date, int] = defaultdict(int)
        for row in rows_for_sunday:
            started = _coerce_utc(row.started_at)
            if not started:
                continue
            if started.weekday() == 6:
                sunday_hours[started.date()] += _session_duration_seconds(row)
        val = 1 if any(secs >= 6 * 3600 for secs in sunday_hours.values()) else 0
        await _apply("secret_sunday", val)

    # --- secret_bilingual: same item with 2+ distinct audio languages ---
    if "secret_bilingual" in by_type:
        bilingual_rows = (await db.execute(
            select(
                PlaybackSession.item_id,
                func.count(distinct(PlaybackSession.audio_language)).label("lang_cnt"),
            )
            .where(
                user_filter, *excl_filters,
                PlaybackSession.audio_language.isnot(None),
            )
            .group_by(PlaybackSession.item_id)
            .having(func.count(distinct(PlaybackSession.audio_language)) >= 2)
        )).all()
        await _apply("secret_bilingual", 1 if bilingual_rows else 0)

    # --- secret_bgNoise: any single session >= 8 hours ---
    if "secret_bgNoise" in by_type:
        rows_for_bg = playback_rows if playback_rows is not None else (
            await db.execute(
                select(PlaybackSession).where(user_filter, *excl_filters)
            )
        ).scalars().all()
        val = 1 if any(
            _session_duration_seconds(r) >= 8 * 3600 for r in rows_for_bg
        ) else 0
        await _apply("secret_bgNoise", val)

    # --- secret_ultramarathon: any single session >= 24 hours ---
    if "secret_ultramarathon" in by_type:
        rows_for_ultra = playback_rows if playback_rows is not None else (
            await db.execute(
                select(PlaybackSession).where(user_filter, *excl_filters)
            )
        ).scalars().all()
        val = 1 if any(
            _session_duration_seconds(r) >= 24 * 3600 for r in rows_for_ultra
        ) else 0
        await _apply("secret_ultramarathon", val)

    # --- secret_butterfly: 5 different genres in one day ---
    if "secret_butterfly" in by_type:
        butterfly_rows = playback_rows if playback_rows is not None else (
            await db.execute(select(PlaybackSession).where(user_filter, *excl_filters))
        ).scalars().all()
        by_day_genres: dict[date, set] = defaultdict(set)
        for row in butterfly_rows:
            started = _coerce_utc(row.started_at)
            if not started or not row.genres:
                continue
            for g in row.genres.split(","):
                g = g.strip()
                if g:
                    by_day_genres[started.date()].add(g)
        val = 1 if any(len(gs) >= 5 for gs in by_day_genres.values()) else 0
        await _apply("secret_butterfly", val)

    # --- secret_triple: 3 movies watched in one day ---
    if "secret_triple" in by_type:
        triple_sub = (
            select(func.date(PlaybackSession.started_at).label("d"))
            .where(user_filter, *excl_filters, PlaybackSession.item_type == "Movie")
            .group_by(func.date(PlaybackSession.started_at))
            .having(func.count(distinct(PlaybackSession.item_id)) >= 3)
            .subquery()
        )
        val = (await db.execute(select(func.count()).select_from(triple_sub))).scalar() or 0
        await _apply("secret_triple", 1 if val > 0 else 0)

    # --- secret_zapper: 5+ different items started in 30 min window ---
    if "secret_zapper" in by_type:
        zapper_rows = (await db.execute(
            select(PlaybackSession.item_id, PlaybackSession.started_at)
            .where(user_filter, *excl_filters)
            .order_by(PlaybackSession.started_at)
        )).all()
        val = 0
        window = timedelta(minutes=30)
        for i in range(len(zapper_rows)):
            start_time = _coerce_utc(zapper_rows[i].started_at)
            if not start_time:
                continue
            items_in_window = set()
            for j in range(i, len(zapper_rows)):
                t = _coerce_utc(zapper_rows[j].started_at)
                if not t or t - start_time > window:
                    break
                items_in_window.add(zapper_rows[j].item_id)
            if len(items_in_window) >= 5:
                val = 1
                break
        await _apply("secret_zapper", val)

    # --- secret_gourmet: noon play every day for 7 consecutive days ---
    if "secret_gourmet" in by_type:
        lunch_rows = (await db.execute(
            select(func.date(PlaybackSession.started_at).label("d"))
            .where(
                user_filter, *excl_filters,
                func.extract("hour", PlaybackSession.started_at) == 12,
            )
            .group_by(func.date(PlaybackSession.started_at))
            .order_by(func.date(PlaybackSession.started_at))
        )).all()
        val = 0
        if len(lunch_rows) >= 7:
            dates_list = [r.d for r in lunch_rows]
            streak_count = 1
            for i in range(1, len(dates_list)):
                if dates_list[i] == dates_list[i - 1] + timedelta(days=1):
                    streak_count += 1
                    if streak_count >= 7:
                        val = 7
                        break
                else:
                    streak_count = 1
        await _apply("secret_gourmet", val)

    # --- secret_ultimate_collector: all OTHER trophies unlocked ---
    if "secret_ultimate_collector" in by_type:
        total_others = sum(1 for a in all_achs if a.id != "secret_ultimate_collector")
        unlocked_others = len(unlocked_ids - {"secret_ultimate_collector"})
        val = 1 if unlocked_others >= total_others and total_others > 0 else 0
        await _apply("secret_ultimate_collector", val)

    # --- secret_purist: sessions whose audio track equals the TMDB
    # original_language. Counted in Python via the ISO 639-1↔639-2 map
    # rather than a CASE in SQL — cleaner and the row volume is bounded
    # to a single user's history.
    if "secret_purist" in by_type:
        rows = (await db.execute(
            select(
                PlaybackSession.audio_language,
                EmbyTmdbIndex.original_language,
            )
            .select_from(PlaybackSession)
            .join(
                EmbyTmdbIndex,
                PlaybackSession.item_id == EmbyTmdbIndex.emby_item_id,
            )
            .where(
                user_filter,
                PlaybackSession.audio_language.isnot(None),
                EmbyTmdbIndex.original_language.isnot(None),
                *excl_filters,
            )
        )).all()
        val = sum(1 for r in rows if audio_matches_original(r[0], r[1]))
        await _apply("secret_purist", val)

    # --- secret_sync: same item watched concurrently with another user ---
    # Anti-trivial guard: a single-user instance can never satisfy the
    # "another user" clause; bail out early so a self-join across the
    # same MK user's multi-device sessions cannot accidentally fire it.
    if "secret_sync" in by_type:
        if not await has_distinct_user_universe(db):
            await _apply("secret_sync", 0)
        else:
            emby_uids = (await db.execute(
                select(distinct(PlaybackSession.user_id)).where(user_filter)
            )).scalars().all()
            if not emby_uids:
                await _apply("secret_sync", 0)
            else:
                hit = await has_same_item_other_user_overlap(db, list(emby_uids))
                await _apply("secret_sync", 1 if hit else 0)

    # --- secret_lonely: a NYE session (Dec 31 / Jan 1 UTC) with no
    # overlapping session from any other user. Same anti-trivial guard
    # as secret_sync — single-user instances skip the check entirely.
    if "secret_lonely" in by_type:
        if not await has_distinct_user_universe(db):
            await _apply("secret_lonely", 0)
        else:
            candidate_rows = (await db.execute(
                select(PlaybackSession).where(
                    user_filter,
                    or_(
                        and_(
                            func.extract("month", PlaybackSession.started_at) == 12,
                            func.extract("day", PlaybackSession.started_at) == 31,
                        ),
                        and_(
                            func.extract("month", PlaybackSession.started_at) == 1,
                            func.extract("day", PlaybackSession.started_at) == 1,
                        ),
                    ),
                    *excl_filters,
                )
            )).scalars().all()

            unlocked = False
            for row in candidate_rows:
                if await find_concurrent_other_user_session(
                    db,
                    user_id=row.user_id,
                    started_at=row.started_at,
                    ended_at=row.ended_at,
                ):
                    continue
                unlocked = True
                break
            await _apply("secret_lonely", 1 if unlocked else 0)

    # --- secret_allnight: chain of sessions covers 22:00 → 06:00 UTC ---
    if "secret_allnight" in by_type:
        emby_uids = (await db.execute(
            select(distinct(PlaybackSession.user_id)).where(user_filter)
        )).scalars().all()
        if not emby_uids:
            await _apply("secret_allnight", 0)
        else:
            hit = await has_all_night_chain(db, list(emby_uids))
            await _apply("secret_allnight", 1 if hit else 0)

    # --- secret_no_life: 24h cumulative within a 48h sliding window ---
    if "secret_no_life" in by_type:
        emby_uids = (await db.execute(
            select(distinct(PlaybackSession.user_id)).where(user_filter)
        )).scalars().all()
        if not emby_uids:
            await _apply("secret_no_life", 0)
        else:
            hit = await has_24h_in_48h_window(db, list(emby_uids))
            await _apply("secret_no_life", 1 if hit else 0)

    # --- secret_king: 12 consecutive months as the strict #1, with the
    # anti-trivial guard (>= 2 distinct active users per qualifying month).
    if "secret_king" in by_type:
        if not await has_distinct_user_universe(db):
            await _apply("secret_king", 0)
        else:
            emby_uids = (await db.execute(
                select(distinct(PlaybackSession.user_id)).where(user_filter)
            )).scalars().all()
            if not emby_uids:
                await _apply("secret_king", 0)
            else:
                hit = await has_12_consecutive_top1_months(db, list(emby_uids))
                await _apply("secret_king", 12 if hit else 0)

    # --- secret_pilot: first viewer on freshly-added content. Anti-trivial
    # guard mirrors secret_sync / secret_lonely / secret_king: a single-user
    # instance can never satisfy the "before anyone else" clause.
    if "secret_pilot" in by_type:
        if not await has_distinct_user_universe(db):
            await _apply("secret_pilot", 0)
        else:
            emby_uids = list((await db.execute(
                select(distinct(PlaybackSession.user_id)).where(user_filter)
            )).scalars().all())
            hit = (
                await is_first_viewer_of_fresh_content(db, emby_uids)
                if emby_uids else False
            )
            await _apply("secret_pilot", 1 if hit else 0)

    # --- secret_late: any session started >= 1 year after the item was
    # added to the library. Pure metadata check on the observed user, no
    # cross-user guard needed.
    if "secret_late" in by_type:
        rows = (await db.execute(
            select(PlaybackSession.started_at, EmbyTmdbIndex.date_created)
            .select_from(PlaybackSession)
            .join(
                EmbyTmdbIndex,
                PlaybackSession.item_id == EmbyTmdbIndex.emby_item_id,
            )
            .where(
                user_filter,
                EmbyTmdbIndex.date_created.isnot(None),
                *excl_filters,
            )
        )).all()
        late_threshold = timedelta(days=365)
        hit = False
        for started, created in rows:
            s = _coerce_utc(started)
            c = _coerce_utc(created)
            if s and c and (s - c) >= late_threshold:
                hit = True
                break
        await _apply("secret_late", 1 if hit else 0)

    return unlocks
