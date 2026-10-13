"""Pause / resume events observed on Emby ``/Sessions``."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackPauseEvent, PlaybackSession

_PAUSE_OPEN_PROOF_WINDOW = timedelta(seconds=90)


async def _process_pause_events(db: AsyncSession, sessions: list, now: datetime):
    """Detect pause/resume transitions on Emby ``/Sessions`` and persist
    them to ``playback_pause_events``.

    A pause event is opened when a session ticks paused with no other
    open event for the same ``session_key``; it is closed (``resumed_at``
    + ``duration_seconds``) when the same key ticks playing again. Both
    sides are idempotent: re-emitted ticks in the same state are
    no-ops, so the table cannot accumulate duplicates from a sticky
    Emby session. Sessions that disappear without a resume tick stay
    open and never become qualifying events.

    Cold-start guard: opening a new event requires recent proof that the
    session was actively playing — an active ``PlaybackSession`` row for
    the same Emby session with a ``last_seen_at`` no older than
    ``_PAUSE_OPEN_PROOF_WINDOW``. Without this guard a session that was
    *already paused* when the collector restarted would have its pause
    clock reset to ``now`` and could close inside the 2-5 minute
    qualifying window even though the user never produced a fresh
    pause/resume cycle. We prefer dropping that pause silently over
    awarding a false positive.

    ``now`` is taken from the caller so tests can drive the function
    deterministically.
    """
    paused_pairs: list[tuple[str, dict]] = []
    playing_keys: set[str] = set()

    for s in sessions:
        np = s.get("NowPlayingItem")
        if not np or not s.get("UserName"):
            continue
        session_key = f"{s.get('UserId', '')}_{np.get('Id', '')}_{s.get('Id', '')}"
        if s.get("PlayState", {}).get("IsPaused", False):
            paused_pairs.append((session_key, s))
        else:
            playing_keys.add(session_key)

    keys = [k for k, _ in paused_pairs] + list(playing_keys)
    if not keys:
        return

    open_rows = (await db.execute(
        select(PlaybackPauseEvent).where(
            PlaybackPauseEvent.session_key.in_(keys),
            PlaybackPauseEvent.resumed_at.is_(None),
        )
    )).scalars().all()
    open_by_key: dict[str, PlaybackPauseEvent] = {ev.session_key: ev for ev in open_rows}

    paused_keys = [k for k, _ in paused_pairs]
    playing_proof: dict[str, PlaybackSession] = {}
    if paused_keys:
        proof_rows = (await db.execute(
            select(PlaybackSession).where(
                PlaybackSession.emby_session_key.in_(paused_keys),
                PlaybackSession.is_active.is_(True),
            )
        )).scalars().all()
        playing_proof = {row.emby_session_key: row for row in proof_rows}

    for session_key, s in paused_pairs:
        if session_key in open_by_key:
            continue
        # Cold-start guard: only open an event when a recent playing
        # tick has been observed for this session_key.
        proof = playing_proof.get(session_key)
        if proof is None or proof.last_seen_at is None:
            continue
        last_seen = proof.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        if (now - last_seen) > _PAUSE_OPEN_PROOF_WINDOW:
            continue
        np = s.get("NowPlayingItem") or {}
        ev = PlaybackPauseEvent(
            session_key=session_key,
            emby_session_id=s.get("Id", "") or None,
            user_id=s.get("UserId", ""),
            user_name=s.get("UserName", ""),
            item_id=np.get("Id", ""),
            item_name=np.get("Name", ""),
            item_type=np.get("Type", ""),
            pause_started_at=now,
        )
        db.add(ev)
        open_by_key[session_key] = ev

    for session_key in playing_keys:
        ev = open_by_key.get(session_key)
        if ev is None or ev.resumed_at is not None:
            continue
        ev.resumed_at = now
        # SQLite returns naive datetimes even when written with tzinfo,
        # so coerce both sides to UTC before subtracting.
        started = ev.pause_started_at
        if started is None:
            delta = 0.0
        else:
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            delta = (now - started).total_seconds()
        ev.duration_seconds = max(0, int(delta))
