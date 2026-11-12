"""Periodic collection of Emby sessions (every ``POLL_INTERVAL_SECONDS``)."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.playback import TICKS_PER_SECOND, WATCH_ITEM_TYPES
from models.playback_stats import LibraryCache, PlaybackSession
from services.emby import get_raw_sessions
from services.portal.gdpr_erased import is_erased, load_erased_identities
from services.settings import get_active_media_source

from ._cache import _normalize_library_name
from ._closure import _grant_post_session_xp
from ._completions import record_completions
from ._measure import (
    FRESH_START_MAX_SECONDS,
    MAX_REOPEN_CREDIT_SECONDS,
    RESUME_WINDOW,
    SILENCE_LIMIT,
    add_to_hour,
    as_utc,
    client_is_alive,
    exclusive_shares,
    fresh_start_seconds,
    measure_progress,
    player_confirms,
)
from ._metadata import genres, session_metadata
from ._pauses import _process_pause_events
from ._player_reports import (
    fetch_stored_positions,
    forget_other_sessions,
    player_is_lost,
    title_key,
)
from ._resolver import _session_library_name
from ._resume_zones import refresh_resume_zones

__all__ = ["_grant_post_session_xp", "_process_pause_events", "collect_active_sessions"]

logger = logging.getLogger("mediakeeper.stats.collector")

# Non-catalogued playback we never track as a watch: Emby Cinema Mode intros
# arrive as Type "Video" and pre-roll trailers as Type "Trailer".
_UNTRACKED_ITEM_TYPES = frozenset({"Video", "Trailer"})


def _tracked(session: dict) -> bool:
    now_playing = session.get("NowPlayingItem")
    return bool(now_playing and session.get("UserName")) and now_playing.get("Type") not in _UNTRACKED_ITEM_TYPES


def _emby_key(session: dict) -> str:
    """Identifies one Emby session playing one item (stable across polls)."""
    return f"{session.get('UserId', '')}_{session['NowPlayingItem'].get('Id', '')}_{session.get('Id', '')}"


async def _open_row(
    db: AsyncSession, session: dict, key: str, position: int, now: datetime,
    url: str, api_key: str, aliases: dict,
) -> PlaybackSession:
    """Start a new row: one per playback, even when the Emby session is reused."""
    item_id = session["NowPlayingItem"].get("Id", "")
    user_id = session.get("UserId", "")
    library = await _session_library_name(session["NowPlayingItem"], item_id, url, api_key, aliases, user_id)
    credit = fresh_start_seconds(position)
    row = PlaybackSession(
        session_key=f"{key}:{int(now.timestamp())}",
        emby_session_key=key,
        user_id=user_id,
        item_id=item_id,
        library_name=library,
        position_ticks=position,
        started_at=now - timedelta(seconds=credit),
        last_seen_at=now,
        is_active=True,
        watched_seconds=credit,
        last_tick_at=now,
        last_tick_position_ticks=position,
        measured=True,
        **session_metadata(session),
    )
    db.add(row)
    return row


async def _refresh_metadata(
    row: PlaybackSession, session: dict, url: str, api_key: str, aliases: dict,
) -> None:
    now_playing = session["NowPlayingItem"]
    if not row.genres:
        row.genres = genres(now_playing)
    if not row.library_name:
        row.library_name = await _session_library_name(
            now_playing, row.item_id, url, api_key, aliases, row.user_id,
        )
        if row.library_name:
            logger.info("Session %s: library_name resolved → %s", row.session_key, row.library_name)


def _is_leftover(lost: bool, position: int, previous: PlaybackSession | None) -> bool:
    """A listed session that is not a playback: Emby moves it alone, or it still
    sits exactly where its last row stopped (an isolated sign of activity)."""
    if lost and position > FRESH_START_MAX_SECONDS * TICKS_PER_SECOND:
        return True
    return previous is not None and position > 0 and previous.position_ticks == position


def _resumable(row: PlaybackSession | None, now: datetime) -> bool:
    """Closed moments ago by a pause that made Emby drop the session. A title
    already watched to the end is never resumed: playing it again is a new
    viewing."""
    seen = as_utc(row.last_seen_at) if row else None
    return seen is not None and row.completed_at is None and seen >= now - RESUME_WINDOW


def _silent_too_long(row: PlaybackSession, now: datetime) -> bool:
    seen = as_utc(row.last_seen_at)
    return seen is not None and now - seen > SILENCE_LIMIT


async def collect_active_sessions(db: AsyncSession, now: datetime | None = None):
    """Measure every tracked Emby session and close the rows whose session is gone.

    ``now`` defaults to the current time; tests pass it to replay a sequence of polls.
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return

    url = source.get("url", "").rstrip("/")
    api_key = source.get("api_key", "")
    if not url or not api_key:
        return

    now = now or datetime.now(timezone.utc)
    # Someone erased at their request is no longer recorded. By Emby id alone: a
    # namesake is refused an account, but still counts in the statistics.
    erased = await load_erased_identities(db)
    sessions = [
        s for s in (await get_raw_sessions(db) or [])
        if _tracked(s) and not is_erased(erased, s.get("UserId"), None)
    ]

    await _process_pause_events(db, sessions, now)
    stored = await fetch_stored_positions(url, api_key, sessions)
    if stored:  # the libraries' resume settings only serve to judge a saved position
        await refresh_resume_zones(url, api_key, now)

    keys = {_emby_key(s) for s in sessions}
    forget_other_sessions(keys)
    active: dict[str, PlaybackSession] = {}
    if keys:
        rows = (await db.execute(
            select(PlaybackSession).where(
                PlaybackSession.emby_session_key.in_(keys),
                PlaybackSession.is_active.is_(True),
            )
        )).scalars().all()
        active = {row.emby_session_key: row for row in rows}

    last_closed: dict[str, PlaybackSession] = {}
    missing = [key for key in keys if key not in active]
    if missing:
        rows = (await db.execute(
            select(PlaybackSession).where(
                PlaybackSession.emby_session_key.in_(missing),
                PlaybackSession.is_active.is_(False),
            ).order_by(PlaybackSession.last_seen_at, PlaybackSession.id)
        )).scalars().all()
        last_closed = {row.emby_session_key: row for row in rows}

    library_rows = (await db.execute(select(LibraryCache.lib_id, LibraryCache.name))).all()
    aliases = {
        "by_id": {str(row.lib_id): row.name for row in library_rows if row.lib_id and row.name},
        "by_name": {_normalize_library_name(row.name): row.name for row in library_rows if row.name},
    }

    progress: list[tuple[PlaybackSession, str, int]] = []
    for s in sessions:
        key = _emby_key(s)
        paused = s.get("PlayState", {}).get("IsPaused", False)
        position = s.get("PlayState", {}).get("PositionTicks") or 0
        row = active.get(key)
        previous = last_closed.get(key)
        lost = player_is_lost(s, key, row, previous, stored.get(title_key(s)), now)
        reopened = False
        if row is None:
            # Only a live, playing player opens a row: a session first seen
            # paused or silent is a leftover, not a new playback.
            if paused or not client_is_alive(s, now) or _is_leftover(lost, position, previous):
                continue
            if not _resumable(previous, now):
                row = active[key] = await _open_row(db, s, key, position, now, url, api_key, aliases)
                progress.append((row, row.user_id, row.watched_seconds))
                continue
            row = active[key] = previous
            row.is_active, row.ended_at = True, None
            reopened = True

        # Lost or silent player: what Emby moves on its own is not counted, and
        # the reference stays on the last confirmed poll, so what the player
        # really played meanwhile (buffer during a network cut) counts once it
        # reports again; nothing counts if it never comes back.
        seconds = 0
        if not lost and player_confirms(s, row.last_tick_at):
            seconds, row.last_tick_at, row.last_tick_position_ticks = measure_progress(
                row.last_tick_position_ticks, row.last_tick_at, position, now, paused=paused,
            )
            if reopened:
                seconds = min(seconds, MAX_REOPEN_CREDIT_SECONDS)
            row.position_ticks = position
            row.watched_seconds = (row.watched_seconds or 0) + seconds
            # The last real playback: it becomes ``ended_at`` when the row closes.
            # Without any position (live channel), activity is all there is.
            if not paused and (seconds > 0 or position == 0):
                row.last_seen_at = now
                await _refresh_metadata(row, s, url, api_key, aliases)
        progress.append((row, row.user_id, seconds))
        if _silent_too_long(row, now):
            del active[key]  # closed below, at its last real second
            logger.info("Playback row %s closed: nothing played for %s (client %s)", row.id, SILENCE_LIMIT, row.client_name)

    video = [entry for entry in progress if entry[0].item_type in WATCH_ITEM_TYPES]
    for row, seconds in exclusive_shares(video).items():
        row.exclusive_seconds = (row.exclusive_seconds or 0) + seconds
        row.watched_by_hour = add_to_hour(row.watched_by_hour, now, seconds)

    await db.flush()
    await record_completions(db, [row for row, _, _ in progress], now)

    stale_query = select(PlaybackSession).where(PlaybackSession.is_active.is_(True))
    if active:
        stale_query = stale_query.where(or_(
            PlaybackSession.emby_session_key.is_(None),
            PlaybackSession.emby_session_key.notin_(list(active)),
        ))
    closed_sessions = []
    for row in (await db.execute(stale_query)).scalars().all():
        row.is_active = False
        # ``last_seen_at`` is the last poll where the session really played,
        # far more accurate than ``now`` after a collector outage.
        row.ended_at = row.last_seen_at or now
        closed_sessions.append(row)

    await db.commit()

    if closed_sessions:
        await _grant_post_session_xp(db, closed_sessions)
