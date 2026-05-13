"""Cinema room — marathon progress + server-authoritative advance.

These tests pin down the gate logic of
``services/portal/mk_events_marathon`` against the in-memory SQLite
engine wired in ``conftest.py``. They cover:

  * snapshot semantics (non-marathon no-op, ratio computation,
    ineligible_count for participants without an Emby identifier),
  * participation gate (creator allowed, accepted member allowed,
    stranger rejected with 403),
  * advance atomicity (stale ``expected_step`` → 409, not-ready → 412
    with the freeze payload, two-in-a-row → second call sees the
    bumped step and bails).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.playback_stats import PlaybackSession
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.event import MKEvent, MKEventInvitation
from models.portal.profile import UserProfile
from models.user import User
from services.portal.mk_events_marathon import (
    MarathonError,
    advance_marathon_step,
    compute_marathon_progress,
)


TICKS = 10_000_000  # 1 second in Emby ticks.


async def _make_user(
    db, *, username: str, emby_user_id: str | None = "emby-default",
) -> User:
    user = User(
        username=username,
        hashed_password=hash_password("MarathonPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
        emby_user_id=(
            f"{emby_user_id}-{user.id}" if emby_user_id else None
        ),
    )
    db.add(profile)
    await db.commit()
    return user


async def _make_event(
    db, *, creator: User, tmdb_items: list[dict], current_step: int = 0,
) -> MKEvent:
    event = MKEvent(
        creator_user_id=creator.id,
        title="Marathon Night",
        kind="private",
        tmdb_ids=tmdb_items,
        scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        status="scheduled",
        current_step=current_step,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def _accept_and_seat(
    db, *, event: MKEvent, user: User, seat: int,
) -> MKEventInvitation:
    inv = MKEventInvitation(
        event_id=event.id,
        user_id=user.id,
        status="accepted",
        invite_count=1,
        seat_index=seat,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


async def _index_tmdb(db, *, emby_item_id: str, tmdb_id: int) -> None:
    row = EmbyTmdbIndex(
        emby_item_id=emby_item_id,
        tmdb_id=tmdb_id,
        media_type="movie",
        title=f"Movie {tmdb_id}",
    )
    db.add(row)
    await db.commit()


async def _record_playback(
    db, *, user: User, emby_item_id: str, position_ticks: int, duration_ticks: int,
) -> None:
    profile = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()
    session = PlaybackSession(
        session_key=f"sess-{user.id}-{emby_item_id}",
        user_id=profile.emby_user_id,
        user_name=profile.display_name,
        item_id=emby_item_id,
        item_name=f"Movie ({emby_item_id})",
        item_type="Movie",
        duration_ticks=duration_ticks,
        position_ticks=position_ticks,
    )
    db.add(session)
    await db.commit()


# ─── compute_marathon_progress ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_single_film_event_is_not_a_marathon(db_session):
    creator = await _make_user(db_session, username="solo-creator")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[{"tmdb_id": 1, "media_type": "movie", "title": "Solo"}],
    )

    result = await compute_marathon_progress(db_session, event.id, creator.id)
    assert result["is_marathon"] is False
    assert result["ready"] is False
    assert result["participants"] == []


@pytest.mark.asyncio
async def test_marathon_no_seated_participants_is_not_ready(db_session):
    creator = await _make_user(db_session, username="empty-creator")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 1, "media_type": "movie", "title": "A"},
            {"tmdb_id": 2, "media_type": "movie", "title": "B"},
            {"tmdb_id": 3, "media_type": "movie", "title": "C"},
        ],
    )
    result = await compute_marathon_progress(db_session, event.id, creator.id)
    assert result["is_marathon"] is True
    assert result["ready"] is False
    assert result["participants"] == []
    assert result["total_steps"] == 3


@pytest.mark.asyncio
async def test_marathon_mixed_progress_blocks_ready(db_session):
    creator = await _make_user(db_session, username="mixed-creator")
    alice = await _make_user(db_session, username="alice")
    bob = await _make_user(db_session, username="bob")

    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 11, "media_type": "movie", "title": "First"},
            {"tmdb_id": 22, "media_type": "movie", "title": "Second"},
        ],
    )
    await _accept_and_seat(db_session, event=event, user=alice, seat=0)
    await _accept_and_seat(db_session, event=event, user=bob, seat=1)
    await _index_tmdb(db_session, emby_item_id="emby-first", tmdb_id=11)

    # Alice at 50%, Bob at 90%.
    duration = 7200 * TICKS  # 2h
    await _record_playback(
        db_session, user=alice, emby_item_id="emby-first",
        position_ticks=int(duration * 0.5), duration_ticks=duration,
    )
    await _record_playback(
        db_session, user=bob, emby_item_id="emby-first",
        position_ticks=int(duration * 0.9), duration_ticks=duration,
    )
    result = await compute_marathon_progress(db_session, event.id, creator.id)
    assert result["is_marathon"] is True
    assert result["ready"] is False
    ratios = sorted(p["ratio"] for p in result["participants"])
    assert ratios == [0.5, 0.9]
    assert result["current_tmdb"]["tmdb_id"] == 11


@pytest.mark.asyncio
async def test_marathon_all_above_threshold_is_ready(db_session):
    creator = await _make_user(db_session, username="ready-creator")
    alice = await _make_user(db_session, username="alice-r")
    bob = await _make_user(db_session, username="bob-r")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 41, "media_type": "movie", "title": "Open"},
            {"tmdb_id": 42, "media_type": "movie", "title": "Close"},
        ],
    )
    await _accept_and_seat(db_session, event=event, user=alice, seat=2)
    await _accept_and_seat(db_session, event=event, user=bob, seat=3)
    await _index_tmdb(db_session, emby_item_id="emby-open", tmdb_id=41)
    duration = 6000 * TICKS
    for user in (alice, bob):
        await _record_playback(
            db_session, user=user, emby_item_id="emby-open",
            position_ticks=int(duration * 0.9), duration_ticks=duration,
        )
    result = await compute_marathon_progress(db_session, event.id, creator.id)
    assert result["ready"] is True
    assert all(p["meets_threshold"] for p in result["participants"])


@pytest.mark.asyncio
async def test_participant_without_emby_id_is_ineligible(db_session):
    creator = await _make_user(db_session, username="elig-creator")
    tracked = await _make_user(db_session, username="tracked")
    untrack = await _make_user(
        db_session, username="untracked", emby_user_id=None,
    )
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 91, "media_type": "movie", "title": "X"},
            {"tmdb_id": 92, "media_type": "movie", "title": "Y"},
        ],
    )
    await _accept_and_seat(db_session, event=event, user=tracked, seat=4)
    await _accept_and_seat(db_session, event=event, user=untrack, seat=5)
    await _index_tmdb(db_session, emby_item_id="emby-x", tmdb_id=91)
    duration = 5400 * TICKS
    await _record_playback(
        db_session, user=tracked, emby_item_id="emby-x",
        position_ticks=int(duration * 0.95), duration_ticks=duration,
    )
    result = await compute_marathon_progress(db_session, event.id, creator.id)
    assert result["ineligible_count"] == 1
    assert len(result["participants"]) == 1
    # ``ready`` reflects only trackable members: one watcher above 85%
    # ⇒ green light, the untracked peer cannot freeze the marathon.
    assert result["ready"] is True


@pytest.mark.asyncio
async def test_non_participant_gets_403(db_session):
    creator = await _make_user(db_session, username="gate-creator")
    stranger = await _make_user(db_session, username="stranger")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[{"tmdb_id": 1, "media_type": "movie", "title": "X"}],
    )
    with pytest.raises(MarathonError) as exc:
        await compute_marathon_progress(db_session, event.id, stranger.id)
    assert exc.value.status_code == 403
    assert exc.value.detail == "not_member"


# ─── advance_marathon_step ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_advance_rejected_for_non_participant(db_session):
    creator = await _make_user(db_session, username="adv-creator")
    stranger = await _make_user(db_session, username="adv-stranger")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 1, "media_type": "movie", "title": "A"},
            {"tmdb_id": 2, "media_type": "movie", "title": "B"},
        ],
    )
    with pytest.raises(MarathonError) as exc:
        await advance_marathon_step(db_session, event.id, stranger.id, 0)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_advance_rejects_stale_expected_step(db_session):
    creator = await _make_user(db_session, username="stale-creator")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 1, "media_type": "movie", "title": "A"},
            {"tmdb_id": 2, "media_type": "movie", "title": "B"},
        ],
        current_step=0,
    )
    with pytest.raises(MarathonError) as exc:
        await advance_marathon_step(db_session, event.id, creator.id, 1)
    assert exc.value.status_code == 409
    assert exc.value.detail == "stale_step"


@pytest.mark.asyncio
async def test_advance_blocked_when_not_all_ready(db_session):
    creator = await _make_user(db_session, username="not-ready-creator")
    member = await _make_user(db_session, username="not-ready-member")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 51, "media_type": "movie", "title": "A"},
            {"tmdb_id": 52, "media_type": "movie", "title": "B"},
        ],
    )
    await _accept_and_seat(db_session, event=event, user=member, seat=0)
    await _index_tmdb(db_session, emby_item_id="emby-51", tmdb_id=51)
    duration = 6000 * TICKS
    await _record_playback(
        db_session, user=member, emby_item_id="emby-51",
        position_ticks=int(duration * 0.5), duration_ticks=duration,
    )
    with pytest.raises(MarathonError) as exc:
        await advance_marathon_step(db_session, event.id, creator.id, 0)
    assert exc.value.status_code == 412
    assert exc.value.detail == "not_all_ready"
    assert exc.value.payload["participants"]


@pytest.mark.asyncio
async def test_advance_bumps_current_step_when_ready(db_session):
    creator = await _make_user(db_session, username="bump-creator")
    member = await _make_user(db_session, username="bump-member")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 61, "media_type": "movie", "title": "A"},
            {"tmdb_id": 62, "media_type": "movie", "title": "B"},
        ],
    )
    await _accept_and_seat(db_session, event=event, user=member, seat=0)
    await _index_tmdb(db_session, emby_item_id="emby-61", tmdb_id=61)
    duration = 6000 * TICKS
    await _record_playback(
        db_session, user=member, emby_item_id="emby-61",
        position_ticks=int(duration * 0.95), duration_ticks=duration,
    )
    result = await advance_marathon_step(db_session, event.id, creator.id, 0)
    assert result["ok"] is True
    assert result["current_step"] == 1
    assert result["event"]["current_step"] == 1


@pytest.mark.asyncio
async def test_advance_collision_second_caller_gets_409(db_session):
    """SQLite serialises writes so two ``advance`` calls in a row let
    us pin down the staleness check: the second caller sees the bumped
    step and bails with 409, instead of double-incrementing."""
    creator = await _make_user(db_session, username="race-creator")
    member = await _make_user(db_session, username="race-member")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[
            {"tmdb_id": 71, "media_type": "movie", "title": "A"},
            {"tmdb_id": 72, "media_type": "movie", "title": "B"},
        ],
    )
    await _accept_and_seat(db_session, event=event, user=member, seat=0)
    await _index_tmdb(db_session, emby_item_id="emby-71", tmdb_id=71)
    duration = 6000 * TICKS
    await _record_playback(
        db_session, user=member, emby_item_id="emby-71",
        position_ticks=int(duration * 0.9), duration_ticks=duration,
    )
    first = await advance_marathon_step(db_session, event.id, creator.id, 0)
    assert first["current_step"] == 1
    with pytest.raises(MarathonError) as exc:
        await advance_marathon_step(db_session, event.id, member.id, 0)
    assert exc.value.status_code == 409


# ─── serializer regression guard ───────────────────────────────────────


@pytest.mark.asyncio
async def test_serializer_exposes_current_step(db_session):
    from services.portal.mk_events_utils import _serialize_event

    creator = await _make_user(db_session, username="serial-creator")
    event = await _make_event(
        db_session, creator=creator,
        tmdb_items=[{"tmdb_id": 1, "media_type": "movie", "title": "S"}],
        current_step=0,
    )
    payload = await _serialize_event(db_session, event)
    assert "current_step" in payload
    assert payload["current_step"] == 0
