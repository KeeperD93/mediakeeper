"""Cross-user concurrency primitives over ``playback_sessions``.

These helpers underpin the ``secret_lonely`` and ``secret_sync`` trophies,
both of which need to know whether *another* user was watching at the
same wall-clock window. The collector polls every ~15s and persists one
row per session, so this module reads from the same table the rest of
the achievements pipeline already trusts — no new data dependency.

Two notes on the design:

* ``PlaybackSession.user_id`` stores the **Emby user_id string**, not
  the internal MediaKeeper ``users.id``. Callers that translate from
  MK to Emby must do it before invoking these helpers (the achievements
  runner only knows the MK user via ``user_filter`` on ``user_name``,
  so the secrets-b module resolves the matching Emby IDs once and
  passes them down).

* ``excl_filters`` (the global exclusion list maintained by the admin
  panel) is intentionally **not** applied to the cross-user side of
  these checks. The exclusions exist to scrub the *observed* user's
  activity from their own stats; whether their viewing happened to
  coincide with somebody else's is a fact of history regardless of
  whether the other party is on the exclusion list.

Date arithmetic is done in Python rather than via SQL ``+ INTERVAL`` so
the helpers behave identically on SQLite (tests) and PostgreSQL (prod).
A session whose ``ended_at`` is ``NULL`` (still active or never closed
by the collector) is treated as if it ran for ``OPEN_SESSION_FALLBACK``
past its ``started_at`` — the same 4h cap the collector itself uses to
reap orphaned rows.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession


OPEN_SESSION_FALLBACK = timedelta(hours=4)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _effective_end(started_at: datetime, ended_at: datetime | None) -> datetime:
    """Closed sessions use ``ended_at``; open ones get a bounded fallback."""
    return ended_at if ended_at is not None else started_at + OPEN_SESSION_FALLBACK


async def has_distinct_user_universe(db: AsyncSession) -> bool:
    """``True`` iff at least 2 distinct Emby user_ids have a recorded session.

    Anti-trivial guard for ``secret_lonely`` and ``secret_sync``: on a
    single-user instance both conditions would fire on every NYE
    session / every replay, which is not the intent of either trophy.
    Mirrors the arbitration applied to ``secret_king`` in Batch 13.
    """
    count = (await db.execute(
        select(func.count(func.distinct(PlaybackSession.user_id)))
    )).scalar() or 0
    return count >= 2


async def find_concurrent_other_user_session(
    db: AsyncSession,
    user_id: str,
    started_at: datetime,
    ended_at: datetime | None,
) -> bool:
    """Is there a session of a *different* Emby user overlapping the window?

    Window: ``[started_at, _effective_end(started_at, ended_at)]``.
    A candidate row overlaps iff
    ``other.started_at < window_end`` AND
    ``_effective_end(other.started_at, other.ended_at) > window_start``.

    The pre-filter on ``other.started_at < window_end`` is pushed down to
    SQL to keep the candidate set small; the closing comparison uses the
    Python-side ``_effective_end`` so the NULL ``ended_at`` fallback
    behaves the same on SQLite and PostgreSQL.
    """
    window_start = _as_utc(started_at)
    if window_start is None:
        return False
    window_end = _effective_end(window_start, _as_utc(ended_at))

    candidates = (await db.execute(
        select(PlaybackSession.started_at, PlaybackSession.ended_at)
        .where(
            PlaybackSession.user_id != user_id,
            PlaybackSession.started_at < window_end,
        )
    )).all()

    for row_started, row_ended in candidates:
        other_start = _as_utc(row_started)
        if other_start is None:
            continue
        other_end = _effective_end(other_start, _as_utc(row_ended))
        if other_end > window_start:
            return True
    return False


async def has_same_item_other_user_overlap(
    db: AsyncSession,
    emby_user_ids: list[str],
) -> bool:
    """``True`` iff one of the user's sessions overlaps another user on the same item.

    Used by ``secret_sync``. ``emby_user_ids`` covers the (possibly
    multi-device) Emby identities tied to the observed MK user. We
    fetch each user's sessions and the candidate set of "other user"
    sessions on the same ``item_id`` and zip them in Python — bounded
    per user, no SQL dialect-specific date arithmetic needed.
    """
    if not emby_user_ids:
        return False

    own_sessions = (await db.execute(
        select(
            PlaybackSession.item_id,
            PlaybackSession.started_at,
            PlaybackSession.ended_at,
        ).where(PlaybackSession.user_id.in_(emby_user_ids))
    )).all()
    if not own_sessions:
        return False

    own_item_ids = {row.item_id for row in own_sessions if row.item_id}
    if not own_item_ids:
        return False

    other_sessions = (await db.execute(
        select(
            PlaybackSession.item_id,
            PlaybackSession.started_at,
            PlaybackSession.ended_at,
        ).where(
            PlaybackSession.item_id.in_(own_item_ids),
            PlaybackSession.user_id.notin_(emby_user_ids),
        )
    )).all()
    if not other_sessions:
        return False

    others_by_item: dict[str, list[tuple[datetime, datetime]]] = {}
    for row in other_sessions:
        ostart = _as_utc(row.started_at)
        if ostart is None:
            continue
        oend = _effective_end(ostart, _as_utc(row.ended_at))
        others_by_item.setdefault(row.item_id, []).append((ostart, oend))

    for row in own_sessions:
        astart = _as_utc(row.started_at)
        if astart is None:
            continue
        aend = _effective_end(astart, _as_utc(row.ended_at))
        for ostart, oend in others_by_item.get(row.item_id, ()):
            if astart < oend and aend > ostart:
                return True
    return False
