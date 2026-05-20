"""Server-authoritative marathon progress + advance for the cinema room.

``compute_marathon_progress`` returns the ratio reached by every seated
participant on the *current* marathon film, derived from the latest
``PlaybackSession`` for the matching TMDB id (via ``EmbyTmdbIndex``).
Participants with no ``UserProfile.emby_user_id`` cannot be tracked and
are excluded from the readiness gate but counted in ``ineligible_count``.

``advance_marathon_step`` bumps ``MKEvent.current_step`` only when every
trackable participant has crossed the 85% threshold; the row is locked
so two clients racing on the "next film" button cannot double-increment.
The 85% threshold is reused verbatim from ``_watch_threshold``.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.event import MKEvent, MKEventInvitation
from models.portal.profile import UserProfile
from models.playback_stats import PlaybackSession
from models.user import User
from services.portal._display_name import resolve_display_name
from services.portal._watch_threshold import (
    WATCHED_THRESHOLD,
    session_meets_threshold,
)
from services.portal.mk_events_utils import _serialize_event, is_currently_in_room

logger = logging.getLogger("mediakeeper.portal.mk_events.marathon")

# Emby tick = 100 ns. 10_000_000 ticks = 1 second.
TICKS_PER_SECOND = 10_000_000


class MarathonError(Exception):
    """Service-level error carrying an HTTP status code + payload."""

    def __init__(self, status_code: int, detail: str, payload: dict | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.payload = payload or {}


async def _participation_gate(
    db: AsyncSession, event: MKEvent, viewer_user_id: int,
) -> None:
    """Raise 403 unless the viewer is a member, the creator, or admin."""
    if event.creator_user_id == viewer_user_id:
        return
    viewer_profile = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == viewer_user_id)
    )).scalar_one_or_none()
    if viewer_profile and viewer_profile.role == "admin":
        return
    inv = (await db.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == viewer_user_id,
            MKEventInvitation.status == "accepted",
        )
    )).scalar_one_or_none()
    if not inv:
        raise MarathonError(403, "not_member")


def _current_media(event: MKEvent) -> dict | None:
    items = event.tmdb_ids or []
    if not items:
        return None
    idx = event.current_step or 0
    if idx >= len(items):
        return None
    media = items[idx]
    if not isinstance(media, dict):
        return None
    return {
        "tmdb_id": media.get("tmdb_id"),
        "media_type": media.get("media_type"),
        "title": media.get("title"),
        "poster_url": media.get("poster_url"),
    }


async def _gather_participant_progress(
    db: AsyncSession,
    event_id: int,
    media_items: list[dict],
    lang: str,
) -> tuple[list[dict], int]:
    """Return ``(participants, ineligible_count)`` for the per-user films.

    Each participant scans the ``PlaybackSession`` matching the TMDB id
    of *their* current ``user_step`` rather than a shared step — that
    way a viewer who finished film 1 can have their bar fill up on film
    2 even while a latecomer's row still shows film 1. ``media_items``
    is the event's full ``tmdb_ids`` list; the lookup falls back to
    item 0 if a participant's ``user_step`` ever lands out of range
    (defensive guard against stale rows).

    Participants without an Emby identifier cannot be tracked, so they
    are excluded from the readiness gate and counted separately in
    ``ineligible_count``. Returning them in ``ready=False`` instead would
    deadlock marathons containing a non-Emby member.
    """
    rows = (await db.execute(
        select(
            MKEventInvitation.user_id,
            MKEventInvitation.user_step,
            User.username,
            UserProfile.display_name,
            UserProfile.display_name_must_set,
            UserProfile.emby_user_id,
        )
        .join(User, User.id == MKEventInvitation.user_id, isouter=True)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == "accepted",
            MKEventInvitation.seat_index.isnot(None),
        )
    )).all()

    participants: list[dict] = []
    ineligible = 0
    for user_id, user_step, username, display, must_set, emby_user_id in rows:
        if not emby_user_id:
            ineligible += 1
            continue
        # Defensive bounds check — a stale ``user_step`` past the last
        # entry shouldn't crash the snapshot, so we clamp it to the
        # first item rather than raising.
        idx = user_step if 0 <= user_step < len(media_items) else 0
        media = media_items[idx] if media_items else None
        tmdb_id = (
            media.get("tmdb_id")
            if isinstance(media, dict) else None
        )
        if not tmdb_id:
            ineligible += 1
            continue
        latest = (await db.execute(
            select(PlaybackSession.position_ticks, PlaybackSession.duration_ticks)
            .select_from(PlaybackSession)
            .join(
                EmbyTmdbIndex,
                PlaybackSession.item_id == EmbyTmdbIndex.emby_item_id,
            )
            .where(
                PlaybackSession.user_id == emby_user_id,
                EmbyTmdbIndex.tmdb_id == tmdb_id,
            )
            .order_by(PlaybackSession.id.desc())
            .limit(1)
        )).first()

        if latest is None:
            ratio = 0.0
            seconds_remaining: int | None = None
            meets = False
        else:
            pos = latest[0] or 0
            dur = latest[1] or 0
            if dur > 0:
                ratio = max(0.0, min(1.0, pos / dur))
                seconds_remaining = max(0, int((dur - pos) / TICKS_PER_SECOND))
            else:
                # Legacy Playback-Reporting row — no canonical runtime so
                # we cannot compute a ratio. ``session_meets_threshold``
                # treats anything ≥ 1 minute as a full watch.
                ratio = 1.0 if session_meets_threshold(pos, dur) else 0.0
                seconds_remaining = None
            meets = session_meets_threshold(pos, dur)

        username_for_display = (
            None if (must_set or display is None) else display
        ) or username
        participants.append({
            "user_id": user_id,
            "display_name": resolve_display_name(
                username_for_display, user_id, lang,
            ),
            # Per-user marathon step (see migration 051). Surfaced to
            # the panel so each row shows its own ``X/Y`` cell and the
            # "En retard" tag fires when ``user_step < current_step``.
            "user_step": user_step,
            "ratio": round(ratio, 4),
            "seconds_remaining": seconds_remaining,
            "meets_threshold": meets,
        })
    return participants, ineligible


async def compute_marathon_progress(
    db: AsyncSession, event_id: int, viewer_user_id: int, lang: str = "fr",
) -> dict:
    """Snapshot of playback progress for the cinema-room poller.

    The payload covers both shapes the cinema room cares about:

    * **Marathon** (``len(tmdb_ids) > 1``): per-participant ratio on the
      *current* film, used by the readiness gate and the per-row time
      remaining. ``is_marathon`` is ``True``.
    * **Single-film** (``len(tmdb_ids) == 1``): same payload, just with
      ``is_marathon=False`` and ``total_steps=1`` so the front-end can
      still render a "Lecture en cours" panel with the live timer.
      Without this branch the panel stayed hidden and the timer only
      appeared after a hard refresh — see the cinema-room polish cycle.
    """
    event = (await db.execute(
        select(MKEvent).where(MKEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        raise MarathonError(404, "not_found")
    await _participation_gate(db, event, viewer_user_id)

    items = event.tmdb_ids or []
    is_marathon = len(items) > 1
    current_step = event.current_step or 0

    # Presence map (user_id -> is_currently_in_room) so the front-end
    # can refresh seat avatars on every progress tick instead of full
    # ``getOne`` round-trips. Returned alongside ``participants`` (which
    # only covers Emby-trackable viewers) so even non-Emby viewers get
    # their avatar painted / hidden in sync.
    presence_rows = (await db.execute(
        select(
            MKEventInvitation.user_id,
            MKEventInvitation.last_seen_at,
        ).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.status == "accepted",
            MKEventInvitation.seat_index.isnot(None),
        )
    )).all()
    presence = [
        {
            "user_id": uid,
            "is_currently_in_room": is_currently_in_room(last_seen),
        }
        for uid, last_seen in presence_rows
    ]

    current_media = _current_media(event)
    if not current_media or current_media["tmdb_id"] is None:
        # No playable media (empty tmdb_ids or step past the end).
        # Surface a benign snapshot rather than 500-ing the poller.
        return {
            "is_marathon": is_marathon,
            "current_step": current_step,
            "total_steps": len(items),
            "current_tmdb": None,
            "participants": [],
            "presence": presence,
            "ready": False,
            "ineligible_count": 0,
        }

    participants, ineligible = await _gather_participant_progress(
        db, event_id, items, lang,
    )
    ready = bool(participants) and all(p["meets_threshold"] for p in participants)
    return {
        "is_marathon": is_marathon,
        "current_step": current_step,
        "total_steps": len(items),
        "current_tmdb": current_media,
        "participants": participants,
        "presence": presence,
        "ready": ready,
        "ineligible_count": ineligible,
    }


async def advance_marathon_step(
    db: AsyncSession,
    event_id: int,
    viewer_user_id: int,
    expected_step: int,
    lang: str = "fr",
) -> dict:
    """Bump ``MKEvent.current_step`` once every trackable participant
    has crossed the 85% threshold.

    Atomicity: the event row is locked with ``SELECT ... FOR UPDATE`` so
    two concurrent callers racing on the same ``expected_step`` cannot
    double-increment — the second one sees the updated step and bails
    with ``409 stale_step``.
    """
    event = (await db.execute(
        select(MKEvent)
        .where(MKEvent.id == event_id)
        .with_for_update()
    )).scalar_one_or_none()
    if not event:
        await db.rollback()
        raise MarathonError(404, "not_found")
    try:
        await _participation_gate(db, event, viewer_user_id)
    except MarathonError:
        await db.rollback()
        raise

    items = list(event.tmdb_ids or [])
    current_step = event.current_step
    # Snapshot the media dict before any rollback expires the ORM state.
    current_media = _current_media(event)
    if len(items) <= 1:
        await db.rollback()
        raise MarathonError(400, "not_a_marathon")
    if current_step != expected_step:
        await db.rollback()
        raise MarathonError(
            409, "stale_step",
            {"current_step": current_step, "expected_step": expected_step},
        )
    if current_step >= len(items) - 1:
        await db.rollback()
        raise MarathonError(400, "already_last")

    if not current_media or current_media["tmdb_id"] is None:
        await db.rollback()
        raise MarathonError(400, "invalid_current_media")
    participants, ineligible = await _gather_participant_progress(
        db, event_id, items, lang,
    )
    if not participants or not all(p["meets_threshold"] for p in participants):
        payload = {
            "participants": [
                {
                    "user_id": p["user_id"],
                    "ratio": p["ratio"],
                    "meets_threshold": p["meets_threshold"],
                }
                for p in participants
            ],
            "threshold": WATCHED_THRESHOLD,
            "ineligible_count": ineligible,
        }
        await db.rollback()
        raise MarathonError(412, "not_all_ready", payload)

    event.current_step = current_step + 1
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {
        "ok": True,
        "current_step": event.current_step,
        "event": await _serialize_event(db, event),
    }
