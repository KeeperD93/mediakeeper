"""Race / atomicity hardening for the MediaKeeper Events membership paths.

These tests run against the in-memory SQLite engine wired in ``conftest.py``.
SQLite serialises writes within the test event loop, so we cannot reproduce
real cross-process contention — the goal is to lock down the single-process
invariants the savepoint / row-lock / atomic-update changes were introduced
to preserve:

  * ``enter_room``  — the ``MKEvent`` row is locked via
                      ``SELECT ... FOR UPDATE`` so the open-window check →
                      membership check → free-seat scan → seat assignment →
                      ``room_opened_at`` stamp run as one atomic sequence.
                      Every non-success exit after the lock rolls back so
                      the row lock is released before return.
  * ``respond``     — public auto-create wraps the INSERT in a SAVEPOINT so
                      a concurrent peer winning ``uq_mk_event_invitation``
                      does not poison the outer session.
  * ``invite_user`` — first-time INSERT wraps in a SAVEPOINT against
                      ``uq_mk_event_invitation``; the re-invite path uses
                      an atomic SQL UPDATE so two parallel re-invitations
                      cannot drop an increment.
"""
from __future__ import annotations

import datetime as _dt
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.portal.event import MKEvent, MKEventInvitation
from models.portal.profile import UserProfile
from models.user import User
from services.portal import mk_events_members as members_mod
from services.portal import mk_events_room as room_mod
from services.portal.mk_events_members import invite_user, respond
from services.portal.mk_events_room import enter_room
from services.portal.mk_events_utils import (
    MAX_INVITE_RETRIES,
    MAX_PARTICIPANTS,
    ROOM_CLOSE_AFTER_HOURS,
)


# SQLite's ``DateTime(timezone=True)`` strips ``tzinfo`` on the way back out,
# so any production code that reads ``event.scheduled_at`` and compares it
# to ``datetime.now(timezone.utc)`` raises TypeError under the test engine.
# This fixture rewrites the module-level ``datetime`` reference inside
# ``mk_events_room`` so ``datetime.now(timezone.utc)`` returns a naive UTC
# value matching what SQLite hands back. Production code (PostgreSQL) is
# untouched — the patch is scoped to the tests that actually exercise the
# clock-sensitive ``enter_room`` path.
@pytest.fixture
def patch_naive_now(monkeypatch):
    real_datetime = _dt.datetime

    class _NaiveUTCDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003 -- mirror the real signature
            return real_datetime.now(timezone.utc).replace(tzinfo=None)

    monkeypatch.setattr(room_mod, "datetime", _NaiveUTCDateTime)
    yield


# ─── helpers ─────────────────────────────────────────────────────────────


async def _make_user(db, *, username: str) -> User:
    user = User(
        username=username,
        hashed_password=hash_password("MKEventsRacePassword123!"),
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
    )
    db.add(profile)
    await db.commit()
    return user


async def _make_event(
    db,
    *,
    creator: User,
    kind: str = "private",
    scheduled_in_minutes: int = 5,
    title: str = "Movie Night",
) -> MKEvent:
    """Create an event scheduled close enough that the room is already open
    (``ROOM_OPEN_BEFORE_MIN`` is 15 min)."""
    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=scheduled_in_minutes)
    event = MKEvent(
        creator_user_id=creator.id,
        title=title,
        kind=kind,
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "Solo"}],
        scheduled_at=scheduled_at,
        status="scheduled",
        max_participants=MAX_PARTICIPANTS,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def _accept_member(db, event_id: int, user_id: int) -> MKEventInvitation:
    """Insert a pre-accepted invitation row directly."""
    inv = MKEventInvitation(
        event_id=event_id,
        user_id=user_id,
        status="accepted",
        invite_count=1,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


def _in_outer_transaction(db) -> bool:
    """Probe the underlying sync ``Session`` directly for transaction state.

    ``AsyncSession.in_transaction()`` proxies through SQLAlchemy machinery
    that, on this stack, can graze expired ORM attributes and surface a
    ``MissingGreenlet`` outside the async loop. Reading the sync session's
    public ``in_transaction()`` is a pure Python state check (it returns
    ``self._transaction is not None``) and is safe to call here.
    """
    return db.sync_session.in_transaction()


# 1. enter_room — seat allocation, idempotent re-entry, no double seats.


@pytest.mark.asyncio
async def test_enter_room_assigns_seat_and_stamps_room_opened_at(
    db_session, patch_naive_now,
):
    creator = await _make_user(db_session, username="enter-creator")
    member = await _make_user(db_session, username="enter-member")
    event = await _make_event(db_session, creator=creator)
    await _accept_member(db_session, event.id, member.id)

    assert event.room_opened_at is None

    result = await enter_room(db_session, event.id, member.id)
    assert result["ok"] is True
    assert isinstance(result["seat_index"], int)
    assert 0 <= result["seat_index"] < MAX_PARTICIPANTS

    fresh_event = (await db_session.execute(
        select(MKEvent)
        .where(MKEvent.id == event.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh_event.room_opened_at is not None, (
        "room_opened_at must be stamped on first successful enter_room"
    )

    fresh_inv = (await db_session.execute(
        select(MKEventInvitation)
        .where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == member.id,
        )
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh_inv.seat_index == result["seat_index"]


@pytest.mark.asyncio
async def test_enter_room_twice_same_user_returns_same_seat(
    db_session, patch_naive_now,
):
    """A user re-entering must keep the seat allocated on the first entry."""
    creator = await _make_user(db_session, username="enter-twice-creator")
    member = await _make_user(db_session, username="enter-twice-member")
    event = await _make_event(db_session, creator=creator)
    await _accept_member(db_session, event.id, member.id)

    first = await enter_room(db_session, event.id, member.id)
    assert first["ok"] is True
    seat_first = first["seat_index"]

    second = await enter_room(db_session, event.id, member.id)
    assert second["ok"] is True
    assert second["seat_index"] == seat_first, (
        "re-entry must reuse the already-assigned seat, not reroll"
    )

    rows = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == member.id,
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].seat_index == seat_first


@pytest.mark.asyncio
async def test_enter_room_assigns_next_sequential_seat(
    db_session, patch_naive_now,
):
    """Allocation is sequential by ``responded_at``: the next entrant
    lands on ``seat_index = count_seated``. After ``_compact_seats``
    (run on every decline / remove) the layout never has gaps, so we
    pre-seed a contiguous block here and assert the new entrant gets
    the next free slot at the trailing edge."""
    creator = await _make_user(db_session, username="enter-no-clash-creator")
    member = await _make_user(db_session, username="enter-no-clash-member")
    event = await _make_event(db_session, creator=creator)

    pre_seeded = MAX_PARTICIPANTS - 1
    for idx in range(pre_seeded):
        peer = await _make_user(db_session, username=f"peer-seat-{idx}")
        db_session.add(MKEventInvitation(
            event_id=event.id,
            user_id=peer.id,
            status="accepted",
            invite_count=1,
            seat_index=idx,
            responded_at=datetime.now(timezone.utc),
        ))
    await _accept_member(db_session, event.id, member.id)
    await db_session.commit()

    result = await enter_room(db_session, event.id, member.id)
    assert result["ok"] is True
    assert result["seat_index"] == pre_seeded, (
        "sequential allocator must place the new entrant at count_seated, "
        "never reuse a taken index"
    )


@pytest.mark.asyncio
async def test_enter_room_full_releases_transaction(
    db_session, patch_naive_now,
):
    """A full room must release the FOR UPDATE row lock before returning."""
    creator = await _make_user(db_session, username="enter-full-creator")
    member = await _make_user(db_session, username="enter-full-member")
    event = await _make_event(db_session, creator=creator)

    # Saturate every seat.
    for idx in range(MAX_PARTICIPANTS):
        peer = await _make_user(db_session, username=f"full-peer-{idx}")
        db_session.add(MKEventInvitation(
            event_id=event.id,
            user_id=peer.id,
            status="accepted",
            invite_count=1,
            seat_index=idx,
        ))
    await _accept_member(db_session, event.id, member.id)
    await db_session.commit()

    result = await enter_room(db_session, event.id, member.id)
    assert result == {"error": "room_full"}
    assert _in_outer_transaction(db_session) is False, (
        "enter_room (room_full) must release the FOR UPDATE lock before return"
    )

    # Sentinel write proves the session is still usable.
    sentinel = await _make_user(db_session, username="enter-full-sentinel")
    assert sentinel.id is not None


@pytest.mark.asyncio
async def test_enter_room_room_not_open_releases_transaction(
    db_session, patch_naive_now,
):
    """Before the open window, no lock must remain held on return."""
    creator = await _make_user(db_session, username="enter-early-creator")
    member = await _make_user(db_session, username="enter-early-member")
    # Schedule far in the future so the open window is closed.
    event = await _make_event(
        db_session, creator=creator, scheduled_in_minutes=24 * 60,
    )
    await _accept_member(db_session, event.id, member.id)

    result = await enter_room(db_session, event.id, member.id)
    assert result["error"] == "room_not_open"
    assert "open_at" in result
    assert _in_outer_transaction(db_session) is False, (
        "enter_room (room_not_open) must release the FOR UPDATE lock"
    )

    sentinel = await _make_user(db_session, username="enter-early-sentinel")
    assert sentinel.id is not None


@pytest.mark.asyncio
async def test_enter_room_not_member_releases_transaction(
    db_session, patch_naive_now,
):
    """A user without an accepted invitation must not keep the row lock."""
    creator = await _make_user(db_session, username="enter-stranger-creator")
    stranger = await _make_user(db_session, username="enter-stranger")
    event = await _make_event(db_session, creator=creator)

    result = await enter_room(db_session, event.id, stranger.id)
    assert result == {"error": "not_member"}
    assert _in_outer_transaction(db_session) is False, (
        "enter_room (not_member) must release the FOR UPDATE lock"
    )

    sentinel = await _make_user(db_session, username="enter-stranger-sentinel")
    assert sentinel.id is not None


@pytest.mark.asyncio
async def test_enter_room_not_found_releases_transaction(
    db_session, patch_naive_now,
):
    """A bogus event_id must still release the autobegun transaction."""
    user = await _make_user(db_session, username="enter-ghost")

    result = await enter_room(db_session, 9999, user.id)
    assert result == {"error": "not_found"}
    assert _in_outer_transaction(db_session) is False, (
        "enter_room (not_found) must release the FOR UPDATE lock"
    )

    sentinel = await _make_user(db_session, username="enter-ghost-sentinel")
    assert sentinel.id is not None


# 2. respond — public auto-create races against uq_mk_event_invitation.


@pytest.mark.asyncio
async def test_respond_public_savepoint_swallows_concurrent_insert(
    db_session, monkeypatch,
):
    """Force-exercise the IntegrityError → SAVEPOINT-rollback path on the
    public auto-create.

    A real race is: two peers receive the public-event broadcast and both
    accept at the same time; both pre-checks see no row, both INSERT, one
    trips ``uq_mk_event_invitation``. We reproduce this in a single
    process by:

    1. Pre-inserting the conflicting invitation row (the "winning peer")
       at status=pending.
    2. Monkeypatching ``_load_invitation`` so the first call returns
       ``None`` (forces the INSERT path) but the reload after
       IntegrityError returns the real winning row (so the function
       continues with the user's decision).
    3. Calling ``respond`` — the INSERT must trip the unique constraint,
       the SAVEPOINT must roll back cleanly, and the function must apply
       the decision on the winning row without leaking the error.
    4. Verifying only one invitation row remains, the user's decision is
       persisted, and the session is still usable via a sentinel write.
    """
    creator = await _make_user(db_session, username="respond-race-creator")
    user = await _make_user(db_session, username="respond-race-user")
    user_id = user.id
    event = await _make_event(db_session, creator=creator, kind="public")
    event_id = event.id

    # Pre-insert the winning peer's row.
    db_session.add(MKEventInvitation(
        event_id=event_id,
        user_id=user_id,
        status="pending",
        invite_count=1,
    ))
    await db_session.commit()

    real_load = members_mod._load_invitation
    calls = {"n": 0}

    async def _patched_load(db, eid, uid):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return await real_load(db, eid, uid)

    monkeypatch.setattr(members_mod, "_load_invitation", _patched_load)

    result = await respond(db_session, event_id, user_id, "accept")
    assert result["ok"] is True

    rows = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event_id,
            MKEventInvitation.user_id == user_id,
        )
    )).scalars().all()
    assert len(rows) == 1, "uq_mk_event_invitation must keep exactly one row"
    assert rows[0].status == "accepted"

    # Sentinel write proves the outer session survived the savepoint dance.
    sentinel = await _make_user(db_session, username="respond-race-sentinel")
    assert sentinel.id is not None


# 3. invite_user — first-time INSERT race + atomic re-invite increment.


@pytest.mark.asyncio
async def test_invite_user_savepoint_swallows_concurrent_insert(
    db_session, monkeypatch,
):
    """Force-exercise the IntegrityError → SAVEPOINT-rollback path on the
    first-time invitation INSERT.

    A real race is: a creator's UI fires two parallel invite requests for
    the same invitee; both pre-checks see no row, both INSERT, one trips
    ``uq_mk_event_invitation``. We reproduce this in a single process by:

    1. Pre-inserting the conflicting invitation row at status=pending.
    2. Monkeypatching ``_load_invitation`` to return ``None`` on the
       initial pre-check and the real winning row on the reload after
       the IntegrityError.
    3. Calling ``invite_user`` — the INSERT must trip the unique
       constraint, the SAVEPOINT must roll back cleanly, the function
       must return ``ok`` *without* sending a duplicate notification
       (the winning peer already notified), and the session must remain
       usable.
    """
    from models.portal.event import MKNotification

    creator = await _make_user(db_session, username="invite-race-creator")
    invitee = await _make_user(db_session, username="invite-race-invitee")
    event = await _make_event(db_session, creator=creator)

    db_session.add(MKEventInvitation(
        event_id=event.id,
        user_id=invitee.id,
        status="pending",
        invite_count=1,
    ))
    await db_session.commit()

    # Baseline notification count for the invitee — the conflict path must
    # not push a second notification when the winning peer already did.
    baseline = (await db_session.execute(
        select(MKNotification).where(MKNotification.user_id == invitee.id)
    )).scalars().all()
    assert baseline == [], "invitee should start with no notifications"

    real_load = members_mod._load_invitation
    calls = {"n": 0}

    async def _patched_load(db, eid, uid):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return await real_load(db, eid, uid)

    monkeypatch.setattr(members_mod, "_load_invitation", _patched_load)

    result = await invite_user(db_session, event.id, creator.id, invitee.id)
    assert result == {"ok": True}

    rows = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == invitee.id,
        )
    )).scalars().all()
    assert len(rows) == 1, "uq_mk_event_invitation must keep exactly one row"
    assert rows[0].invite_count == 1, (
        "winning peer's invite_count must remain 1 — savepoint absorbed the "
        "second invite path without bumping anything"
    )

    notifs_after = (await db_session.execute(
        select(MKNotification).where(MKNotification.user_id == invitee.id)
    )).scalars().all()
    assert notifs_after == [], (
        "the savepoint conflict path must not send a duplicate notification"
    )

    # Sentinel write proves the outer session survived.
    sentinel = await _make_user(db_session, username="invite-race-sentinel")
    assert sentinel.id is not None


@pytest.mark.asyncio
async def test_invite_user_reinvite_uses_atomic_increment(
    db_session, monkeypatch,
):
    """Two parallel re-invitations must not drop an increment.

    The atomic SQL UPDATE reads the live DB ``invite_count`` and bumps
    it with ``invite_count + 1``, not a stale ORM snapshot. We simulate
    a stale snapshot by monkeypatching ``_load_invitation`` to return an
    invitation instance whose ``invite_count`` is still 1, while the DB
    truly holds 2. The function must persist 3 (live 2 + 1), not 2
    (stale 1 + 1), proving the increment came from the DB.
    """
    creator = await _make_user(db_session, username="reinvite-creator")
    invitee = await _make_user(db_session, username="reinvite-invitee")
    event = await _make_event(db_session, creator=creator)

    inv = MKEventInvitation(
        event_id=event.id,
        user_id=invitee.id,
        status="pending",
        invite_count=2,
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    inv_id = inv.id

    # Forge a stale snapshot at invite_count=1 so a naïve "ORM read +
    # +=1 + write back" implementation would persist 2 (overwriting the
    # live 2 the DB holds).
    async def _stale_load(db, eid, uid):
        return MKEventInvitation(
            id=inv_id,
            event_id=eid,
            user_id=uid,
            status="pending",
            invite_count=1,
        )

    monkeypatch.setattr(members_mod, "_load_invitation", _stale_load)

    result = await invite_user(db_session, event.id, creator.id, invitee.id)
    assert result == {"ok": True}

    fresh = (await db_session.execute(
        select(MKEventInvitation)
        .where(MKEventInvitation.id == inv_id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.invite_count == 3, (
        "atomic UPDATE must use DB invite_count (2 + 1 = 3), not stale ORM "
        "snapshot (1 + 1 = 2)"
    )


@pytest.mark.asyncio
async def test_invite_user_reinvite_caps_at_max_retries(db_session):
    """Sequential re-invites reach the cap and the next call refuses."""
    creator = await _make_user(db_session, username="cap-creator")
    invitee = await _make_user(db_session, username="cap-invitee")
    event = await _make_event(db_session, creator=creator)

    # First call inserts the row at invite_count=1.
    first = await invite_user(db_session, event.id, creator.id, invitee.id)
    assert first == {"ok": True}

    # Bring it to the cap by issuing the remaining re-invitations.
    for _ in range(MAX_INVITE_RETRIES - 1):
        await invite_user(db_session, event.id, creator.id, invitee.id)

    fresh = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == invitee.id,
        )
    )).scalar_one()
    assert fresh.invite_count == MAX_INVITE_RETRIES

    capped = await invite_user(db_session, event.id, creator.id, invitee.id)
    assert capped == {"error": "max_retries_reached"}


# 4. event_ended cutoff — enter_room and respond(accept) reject stale events.


@pytest.mark.asyncio
async def test_enter_room_rejects_event_past_close_cutoff(
    db_session, patch_naive_now,
):
    """An event scheduled long enough ago to be past ``ROOM_CLOSE_AFTER_HOURS``
    must return ``event_ended`` even if its ``status`` row is still
    ``scheduled`` (no autonomous closer job runs yet)."""
    creator = await _make_user(db_session, username="ended-creator")
    member = await _make_user(db_session, username="ended-member")
    scheduled_at = datetime.now(timezone.utc) - timedelta(
        hours=ROOM_CLOSE_AFTER_HOURS + 2,
    )
    event = MKEvent(
        creator_user_id=creator.id,
        title="Past Movie Night",
        kind="private",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "Old"}],
        scheduled_at=scheduled_at,
        status="scheduled",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    await _accept_member(db_session, event.id, member.id)

    result = await enter_room(db_session, event.id, member.id)
    assert result == {"error": "event_ended"}


@pytest.mark.asyncio
async def test_respond_accept_rejects_event_past_close_cutoff(db_session):
    """``respond('accept')`` on a stale event must short-circuit before the
    invitation row is mutated so the user can't drag themselves into a dead
    cinema room from a leftover notification. Decline stays open so they
    can tidy the notification anyway."""
    creator = await _make_user(db_session, username="ended-respond-creator")
    member = await _make_user(db_session, username="ended-respond-member")
    scheduled_at = datetime.now(timezone.utc) - timedelta(
        hours=ROOM_CLOSE_AFTER_HOURS + 2,
    )
    event = MKEvent(
        creator_user_id=creator.id,
        title="Past Movie Night",
        kind="private",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "Old"}],
        scheduled_at=scheduled_at,
        status="scheduled",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    pending = MKEventInvitation(
        event_id=event.id,
        user_id=member.id,
        status="pending",
        invite_count=1,
    )
    db_session.add(pending)
    await db_session.commit()

    result = await respond(db_session, event.id, member.id, "accept")
    assert result == {"error": "event_ended"}

    # Decline is still possible — viewers can tidy stale notifications.
    decline_result = await respond(db_session, event.id, member.id, "decline")
    assert decline_result.get("ok") is True


# 5. _serialize_event — surfaces a per-invitation avatar_url so the
#    cinema seats UI can render the same avatar as the Users panel.


@pytest.mark.asyncio
async def test_serialize_event_exposes_per_invitation_avatar_url(db_session):
    """Each accepted invitation must carry its resolver-correct avatar:
    a custom upload becomes ``/api/portal/avatars/<file>`` (the Emby URL
    is bypassed), while a user with only an Emby-proxied URL keeps it
    untouched. A user with no avatar at all surfaces ``None`` so the
    front-end can fall back to the username initial."""
    from services.portal.mk_events_utils import _serialize_event

    creator = await _make_user(db_session, username="srlz-creator")
    custom_user = await _make_user(db_session, username="srlz-custom")
    emby_user = await _make_user(db_session, username="srlz-emby")
    blank_user = await _make_user(db_session, username="srlz-blank")
    event = await _make_event(db_session, creator=creator)

    # Stamp distinct avatar sources on each profile.
    custom_profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == custom_user.id)
    )).scalar_one()
    custom_profile.avatar_custom_path = "abc123.png"
    custom_profile.avatar_url = "https://emby.example/avatar/should-be-ignored"
    emby_profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == emby_user.id)
    )).scalar_one()
    emby_profile.avatar_url = "https://emby.example/avatar/emby-only.png"
    await db_session.commit()

    await _accept_member(db_session, event.id, custom_user.id)
    await _accept_member(db_session, event.id, emby_user.id)
    await _accept_member(db_session, event.id, blank_user.id)

    payload = await _serialize_event(db_session, event)
    by_user = {inv["user_id"]: inv for inv in payload["invitations"]}

    assert by_user[custom_user.id]["avatar_url"] == "/api/portal/avatars/abc123.png", (
        "a custom upload must win over the Emby URL"
    )
    assert by_user[emby_user.id]["avatar_url"] == "https://emby.example/avatar/emby-only.png", (
        "with no custom upload the Emby-proxied URL is forwarded as-is"
    )
    assert by_user[blank_user.id]["avatar_url"] is None, (
        "no avatar source → None so the UI can fall back to the initial"
    )




# 6. Presence + per-user marathon advance.


@pytest.mark.asyncio
async def test_enter_room_stamps_last_seen_at_and_seeds_user_step(
    db_session, patch_naive_now,
):
    """A first entry must stamp ``last_seen_at`` so peers see the avatar
    immediately, and seed ``user_step`` to the event's current step so
    a latecomer drops in on the film the group is currently watching."""
    creator = await _make_user(db_session, username="presence-seed-creator")
    member = await _make_user(db_session, username="presence-seed-member")
    event = await _make_event(db_session, creator=creator)
    # Group has already advanced once before the latecomer joins.
    event.current_step = 1
    db_session.add(event)
    await db_session.commit()
    await _accept_member(db_session, event.id, member.id)

    result = await enter_room(db_session, event.id, member.id)
    assert result["ok"] is True

    fresh_inv = (await db_session.execute(
        select(MKEventInvitation)
        .where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == member.id,
        )
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh_inv.last_seen_at is not None
    assert fresh_inv.user_step == 1, (
        "first-time entrant must inherit the group-wide current_step"
    )


@pytest.mark.asyncio
async def test_heartbeat_bumps_last_seen_at(db_session, patch_naive_now):
    """Calling ``heartbeat`` advances ``last_seen_at`` past the prior stamp."""
    from services.portal.mk_events_presence import heartbeat as do_heartbeat

    creator = await _make_user(db_session, username="hb-creator")
    member = await _make_user(db_session, username="hb-member")
    event = await _make_event(db_session, creator=creator)
    await _accept_member(db_session, event.id, member.id)
    await enter_room(db_session, event.id, member.id)

    fresh = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == member.id,
        ).execution_options(populate_existing=True)
    )).scalar_one()
    initial_stamp = fresh.last_seen_at
    assert initial_stamp is not None

    # Roll the clock forward so the next heartbeat lands on a later stamp
    # even on systems with low-resolution monotonic clocks.
    fresh.last_seen_at = initial_stamp - _dt.timedelta(seconds=2)
    db_session.add(fresh)
    await db_session.commit()

    result = await do_heartbeat(db_session, event.id, member.id)
    assert result == {"ok": True}

    fresh = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == member.id,
        ).execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.last_seen_at > initial_stamp - _dt.timedelta(seconds=2)


@pytest.mark.asyncio
async def test_leave_clears_last_seen_at_but_preserves_seat(
    db_session, patch_naive_now,
):
    """``leave_room`` drops the live presence flag (avatar hidden for
    peers) but keeps ``seat_index`` so a returning viewer reclaims the
    same seat instead of being shuffled to a new one."""
    from services.portal.mk_events_presence import leave_room as do_leave

    creator = await _make_user(db_session, username="leave-creator")
    member = await _make_user(db_session, username="leave-member")
    event = await _make_event(db_session, creator=creator)
    await _accept_member(db_session, event.id, member.id)
    entry = await enter_room(db_session, event.id, member.id)
    seat_at_entry = entry["seat_index"]

    result = await do_leave(db_session, event.id, member.id)
    assert result == {"ok": True}

    fresh = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == member.id,
        ).execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.last_seen_at is None
    assert fresh.seat_index == seat_at_entry, (
        "leaving the room preserves the seat so re-entry hits the same one"
    )


@pytest.mark.asyncio
async def test_advance_self_bumps_user_step_and_resyncs_event_max(
    db_session, patch_naive_now,
):
    """``advance_self_step`` increments only the caller's ``user_step``
    and resyncs ``MKEvent.current_step`` to ``max(user_step)`` across
    every accepted, seated invitation — peers stay on their own film."""
    from services.portal.mk_events_presence import advance_self_step

    creator = await _make_user(db_session, username="adv-creator")
    fast = await _make_user(db_session, username="adv-fast")
    slow = await _make_user(db_session, username="adv-slow")
    event = await _make_event(db_session, creator=creator)
    # Marathon: 3 films.
    event.tmdb_ids = [
        {"tmdb_id": 1, "media_type": "movie", "title": "A"},
        {"tmdb_id": 2, "media_type": "movie", "title": "B"},
        {"tmdb_id": 3, "media_type": "movie", "title": "C"},
    ]
    db_session.add(event)
    await db_session.commit()
    await _accept_member(db_session, event.id, fast.id)
    await _accept_member(db_session, event.id, slow.id)
    await enter_room(db_session, event.id, fast.id)
    await enter_room(db_session, event.id, slow.id)

    result = await advance_self_step(db_session, event.id, fast.id)
    assert result["ok"] is True
    assert result["user_step"] == 1
    assert result["current_step"] == 1, (
        "event-wide current_step must follow the furthest viewer"
    )

    slow_inv = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == slow.id,
        )
    )).scalar_one()
    assert slow_inv.user_step == 0, (
        "advancing one viewer must NOT bump their peers"
    )


@pytest.mark.asyncio
async def test_advance_self_refuses_past_last_step(
    db_session, patch_naive_now,
):
    """A viewer who has already reached the last film gets a clean 400
    instead of overflowing ``user_step``."""
    from services.portal.mk_events_presence import (
        PresenceError, advance_self_step,
    )

    creator = await _make_user(db_session, username="last-creator")
    member = await _make_user(db_session, username="last-member")
    event = await _make_event(db_session, creator=creator)
    event.tmdb_ids = [
        {"tmdb_id": 1, "media_type": "movie", "title": "A"},
        {"tmdb_id": 2, "media_type": "movie", "title": "B"},
    ]
    db_session.add(event)
    await db_session.commit()
    await _accept_member(db_session, event.id, member.id)
    await enter_room(db_session, event.id, member.id)
    # Bump to the last film manually.
    inv = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == member.id,
        )
    )).scalar_one()
    inv.user_step = 1
    db_session.add(inv)
    await db_session.commit()

    with pytest.raises(PresenceError) as excinfo:
        await advance_self_step(db_session, event.id, member.id)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "already_last"


# 7. Per-event capacity + centered allocation + compact-on-decline.


@pytest.mark.asyncio
async def test_enter_room_allocates_sequential_seats(
    db_session, patch_naive_now,
):
    """Three viewers entering in a row land on seat_index 1, 2, 3 — the
    creator already holds seat 0 from ``_make_event``. Combined with
    ``_compact_seats`` on decline this keeps the cinema layout centred."""
    creator = await _make_user(db_session, username="seq-creator")
    alice = await _make_user(db_session, username="seq-alice")
    bob = await _make_user(db_session, username="seq-bob")
    carol = await _make_user(db_session, username="seq-carol")
    event = await _make_event(db_session, creator=creator)
    await _accept_member(db_session, event.id, creator.id)
    await _accept_member(db_session, event.id, alice.id)
    await _accept_member(db_session, event.id, bob.id)
    await _accept_member(db_session, event.id, carol.id)

    a = await enter_room(db_session, event.id, creator.id)
    b = await enter_room(db_session, event.id, alice.id)
    c = await enter_room(db_session, event.id, bob.id)
    d = await enter_room(db_session, event.id, carol.id)

    assert a["seat_index"] == 0
    assert b["seat_index"] == 1
    assert c["seat_index"] == 2
    assert d["seat_index"] == 3


@pytest.mark.asyncio
async def test_decline_compacts_remaining_seats(
    db_session, patch_naive_now,
):
    """When a seated viewer declines, the remaining seats are compacted
    to 0..N-1 (option B rebalance). Used by the cinema layout to keep
    avatars at the centre regardless of who leaves."""
    from services.portal.mk_events_members import respond

    creator = await _make_user(db_session, username="cmp-creator")
    alice = await _make_user(db_session, username="cmp-alice")
    bob = await _make_user(db_session, username="cmp-bob")
    event = await _make_event(db_session, creator=creator)
    await _accept_member(db_session, event.id, creator.id)
    await _accept_member(db_session, event.id, alice.id)
    await _accept_member(db_session, event.id, bob.id)
    await enter_room(db_session, event.id, creator.id)  # seat 0
    await enter_room(db_session, event.id, alice.id)    # seat 1
    await enter_room(db_session, event.id, bob.id)      # seat 2

    # Alice declines → her seat 1 should be freed and bob's seat 2
    # should collapse to 1 so the block stays contiguous.
    res = await respond(db_session, event.id, alice.id, "decline")
    assert res.get("ok") is True

    bob_inv = (await db_session.execute(
        select(MKEventInvitation).where(
            MKEventInvitation.event_id == event.id,
            MKEventInvitation.user_id == bob.id,
        ).execution_options(populate_existing=True)
    )).scalar_one()
    assert bob_inv.seat_index == 1, (
        "Bob's seat must compact from 2 → 1 after Alice declines"
    )


@pytest.mark.asyncio
async def test_serialize_event_exposes_is_full_when_capacity_reached(
    db_session, patch_naive_now,
):
    """``is_full`` flips true once ``accepted_count >= max_participants``.
    Public event cards rely on this to swap the signup CTA for the
    'Complet' badge."""
    from services.portal.mk_events_utils import _serialize_event

    creator = await _make_user(db_session, username="full-creator")
    event = await _make_event(db_session, creator=creator)
    event.max_participants = 5
    db_session.add(event)
    await db_session.commit()
    await _accept_member(db_session, event.id, creator.id)
    for i in range(4):
        peer = await _make_user(db_session, username=f"full-peer-{i}")
        await _accept_member(db_session, event.id, peer.id)

    payload = await _serialize_event(db_session, event)
    assert payload["max_participants"] == 5
    assert payload["accepted_count"] == 5
    assert payload["is_full"] is True


@pytest.mark.asyncio
async def test_admin_settings_capacity_bounds_snap_to_step_5(db_session):
    """Capacity bounds always land on a step-5 multiple, even if the
    admin pushes 7 in a PATCH. ``update_portal_settings`` snaps the
    value and re-orders ``min > max`` if needed."""
    from services.portal.admin import (
        get_event_capacity_bounds,
        update_portal_settings,
    )

    # Default bounds before any admin write.
    lo, hi = await get_event_capacity_bounds(db_session)
    assert lo == 5 and hi == 20

    await update_portal_settings(db_session, {
        "portal.events.max_participants_min": 7,
        "portal.events.max_participants_max": 18,
    })
    lo, hi = await get_event_capacity_bounds(db_session)
    assert lo == 5, "7 snaps down to the nearest step-5 multiple (5)"
    assert hi == 20, "18 snaps up to the nearest step-5 multiple (20)"

    # min pushed above max in a single PATCH → max bumps to match min.
    await update_portal_settings(db_session, {
        "portal.events.max_participants_min": 15,
        "portal.events.max_participants_max": 10,
    })
    lo, hi = await get_event_capacity_bounds(db_session)
    assert lo == 15 and hi == 15


# 8. Private-doc reference scrubbed from public modules.


@pytest.mark.asyncio
async def test_no_private_doc_reference_in_touched_modules():
    """The reference to the internal planning document previously sitting
    in the public events facade must be scrubbed; the modules touched by
    this batch must not name it. The marker is built from parts so this
    test file itself does not embed the literal string."""
    from pathlib import Path

    backend_root = Path(__file__).resolve().parent.parent
    files = [
        backend_root / "services" / "portal" / "mk_events.py",
        backend_root / "services" / "portal" / "mk_events_members.py",
        backend_root / "services" / "portal" / "mk_events_room.py",
    ]
    private_marker = "ROAD" + "MAP"
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert private_marker not in text, (
            f"{path} still names the private planning document"
        )
