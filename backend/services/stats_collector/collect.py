"""Periodic collection of Emby sessions (every ~15s)."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import LibraryCache, PlaybackSession
from services.emby import get_raw_sessions
from services.settings import get_active_media_source

from ._cache import _normalize_library_name
from ._resolver import _resolve_library_name

logger = logging.getLogger("mediakeeper.stats.collector")


async def collect_active_sessions(db: AsyncSession):
    """
    Called every ~15s. Reuses the shared Emby /Sessions cache,
    creates or updates PlaybackSession rows.
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return

    now = datetime.now(timezone.utc)

    sessions = await get_raw_sessions(db) or []

    active_keys = set()
    candidate_session_keys = []
    library_rows = (await db.execute(select(LibraryCache.lib_id, LibraryCache.name))).all()
    library_aliases = {
        "by_id": {str(row.lib_id): row.name for row in library_rows if row.lib_id and row.name},
        "by_name": {_normalize_library_name(row.name): row.name for row in library_rows if row.name},
    }

    for s in sessions:
        np = s.get("NowPlayingItem")
        if not np or not s.get("UserName"):
            continue
        if s.get("PlayState", {}).get("IsPaused", False):
            continue
        candidate_session_keys.append(f"{s.get('UserId', '')}_{np.get('Id', '')}_{s.get('Id', '')}")

    existing_rows = {}
    if candidate_session_keys:
        existing_res = await db.execute(
            select(PlaybackSession).where(PlaybackSession.session_key.in_(candidate_session_keys))
        )
        existing_rows = {row.session_key: row for row in existing_res.scalars().all()}

    for s in sessions:
        np = s.get("NowPlayingItem")
        if not np or not s.get("UserName"):
            continue

        play_state = s.get("PlayState", {})
        if play_state.get("IsPaused", False):
            continue

        user_id = s.get("UserId", "")
        item_id = np.get("Id", "")
        session_key = f"{user_id}_{item_id}_{s.get('Id', '')}"
        active_keys.add(session_key)

        play_method = "DirectPlay"
        transcode_reasons = s.get("TranscodingInfo", {})
        if transcode_reasons:
            play_method = "Transcode"
        elif play_state.get("PlayMethod") == "DirectStream":
            play_method = "DirectStream"
        elif play_state.get("PlayMethod"):
            play_method = play_state["PlayMethod"]

        media_streams = np.get("MediaStreams", [])
        video_stream = next((ms for ms in media_streams if ms.get("Type") == "Video"), {})
        audio_stream = next((ms for ms in media_streams if ms.get("Type") == "Audio"), {})
        subtitle_stream = next((ms for ms in media_streams if ms.get("Type") == "Subtitle" and ms.get("IsExternal", False) is False), None)
        if not subtitle_stream:
            subtitle_stream = next((ms for ms in media_streams if ms.get("Type") == "Subtitle"), None)

        height = video_stream.get("Height", 0)
        resolution = "4K" if height >= 2100 else "1080p" if height >= 1000 else "720p" if height >= 700 else "SD" if height > 0 else None

        audio_language = audio_stream.get("Language") or audio_stream.get("DisplayLanguage") or None
        subtitle_language = subtitle_stream.get("Language") or subtitle_stream.get("DisplayLanguage") if subtitle_stream else None
        genres_list = np.get("Genres") or np.get("GenreItems") or []
        if genres_list and isinstance(genres_list[0], dict):
            genres_list = [g.get("Name", "") for g in genres_list]
        genres_str = ",".join(g for g in genres_list if g) if genres_list else None

        row = existing_rows.get(session_key)

        if row:
            row.last_seen_at = now
            row.position_ticks = play_state.get("PositionTicks", 0)
            row.is_active = True
            if not row.genres and genres_str:
                row.genres = genres_str
            if not row.library_name:
                lib_name = np.get("LibraryName") or np.get("ParentName") or None
                if not lib_name:
                    lib_name = await _resolve_library_name(item_id, url, api_key, library_aliases)
                if lib_name:
                    logger.info(f"Session {session_key}: library_name enrichi → {lib_name}")
                row.library_name = lib_name
        else:
            lib_name = np.get("LibraryName") or np.get("ParentName") or None
            if lib_name:
                logger.debug(f"New session {item_id}: LibraryName Emby = {lib_name}")
            else:
                lib_name = await _resolve_library_name(item_id, url, api_key, library_aliases)
                logger.info(f"New session {item_id}: library_name resolved = {lib_name}")
            row = PlaybackSession(
                session_key=session_key,
                user_id=user_id,
                user_name=s.get("UserName", ""),
                item_id=item_id,
                item_name=np.get("Name", ""),
                item_type=np.get("Type", ""),
                series_name=np.get("SeriesName"),
                season_number=np.get("ParentIndexNumber"),
                episode_number=np.get("IndexNumber"),
                library_name=lib_name,
                client_name=s.get("Client", ""),
                device_name=s.get("DeviceName", ""),
                ip_address=s.get("RemoteEndPoint", ""),
                play_method=play_method,
                container=np.get("Container", ""),
                video_codec=video_stream.get("Codec", "").upper() or None,
                audio_codec=audio_stream.get("Codec", "").upper() or None,
                resolution=resolution,
                bitrate=np.get("Bitrate") or video_stream.get("BitRate"),
                audio_language=audio_language,
                subtitle_language=subtitle_language,
                genres=genres_str,
                duration_ticks=np.get("RunTimeTicks", 0),
                position_ticks=play_state.get("PositionTicks", 0),
                started_at=now,
                last_seen_at=now,
                is_active=True,
            )
            db.add(row)
            existing_rows[session_key] = row

    stale_query = select(PlaybackSession).where(PlaybackSession.is_active == True)  # noqa: E712
    if active_keys:
        stale_query = stale_query.where(PlaybackSession.session_key.notin_(active_keys))
    stale = await db.execute(stale_query)
    closed_sessions = []
    for row in stale.scalars().all():
        row.is_active = False
        # ``last_seen_at`` is bumped on every poll where the session was
        # still present in Emby, so it's the most accurate signal of when
        # the user actually stopped — much better than ``now``, which can
        # be hours/days late if the collector was down or the container
        # restarted (any session left ``is_active=True`` would otherwise
        # gain that whole window of fake watch time, falsely unlocking
        # the Marathon trophies).
        row.ended_at = row.last_seen_at or now
        closed_sessions.append(row)

    await db.commit()

    if closed_sessions:
        await _grant_post_session_xp(db, closed_sessions)


async def _grant_post_session_xp(db: AsyncSession, closed_sessions: list):
    """Grant XP for completed sessions (anti-abuse checks inside grant_watch_xp).

    Two-stage gate:
    - Lazy-provision: when the Emby username has no MediaKeeper row yet
      we create one so the user is visible in the admin panel — initial
      state is ``account_active=False`` (silent shadow account).
    - XP gate: profiles with ``account_active=True`` always earn XP.
      Profiles with ``account_active=False`` only earn when the admin
      explicitly opted in via ``can_earn_xp_offline`` (migration 035) —
      useful for tracking Emby activity of someone who never logs into
      MK. Otherwise watches accumulate in ``playback_sessions`` only.
    """
    try:
        from models.portal.profile import UserProfile
        from services.portal.xp import grant_watch_xp
        from services.portal.user_import import ensure_user_for_emby_session
        from services.stats import get_exclusions

        excl_list = await get_exclusions(db)
        excluded_names = set()
        for exc in excl_list:
            if exc.get("mode") == "exact":
                excluded_names.add(exc.get("value", ""))

        for sess in closed_sessions:
            if sess.item_name and sess.item_name in excluded_names:
                continue

            user = await ensure_user_for_emby_session(
                db,
                emby_username=sess.user_name,
                emby_user_id=sess.user_id,
            )
            if not user:
                continue

            profile = (await db.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )).scalar_one_or_none()
            if not profile:
                continue
            # XP gate: profiles with ``account_active=True`` always earn.
            # Profiles with ``account_active=False`` only earn when the admin
            # explicitly opted in via ``can_earn_xp_offline`` — useful for
            # tracking Emby activity of someone who never logs into MK.
            if not profile.account_active and not profile.can_earn_xp_offline:
                continue

            wall_duration = 0
            if sess.started_at and sess.ended_at:
                wall_duration = int(
                    (sess.ended_at - sess.started_at).total_seconds()
                )
            position_duration = int((sess.position_ticks or 0) / 10_000_000)
            duration = max(wall_duration, position_duration)
            await grant_watch_xp(
                db,
                user_id=user.id,
                item_id=sess.item_id or "",
                item_type=sess.item_type or "Movie",
                duration_seconds=duration,
                runtime_ticks=sess.duration_ticks,
            )

            try:
                from services.portal.achievements import check_all_achievements
                await check_all_achievements(db, user.id, sess.user_name)
            except Exception as ach_err:
                logger.warning(
                    f"[ACHIEVEMENT] check error user={user.id} "
                    f"emby={sess.user_name}: {ach_err}",
                    exc_info=True,
                )
    except Exception as e:
        logger.warning(f"[XP] post-session XP grant error: {e}", exc_info=True)
