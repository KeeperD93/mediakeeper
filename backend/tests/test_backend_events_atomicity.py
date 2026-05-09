"""Race / atomicity hardening for seasonal-progress and watch-party paths.

These tests run against the in-memory SQLite engine wired in ``conftest.py``.
SQLite serialises writes within the test event loop, so we cannot reproduce
real cross-process contention — the goal is to lock down the single-process
invariants the savepoint / atomic-update / row-lock changes were introduced
to preserve:

  * ``update_event_progress`` — initial INSERT on ``uq_seasonal_progress``
                                is wrapped in a SAVEPOINT so a peer that
                                beat us to the row does not poison the
                                session; subsequent increments use a keyed
                                SQL UPDATE so the live DB ``progress`` is
                                bumped, not a stale ORM snapshot. The
                                ``completed`` flag flips to True the first
                                time the post-increment count crosses
                                ``target_count`` and stays True.
  * ``join_party``            — the ``WatchParty`` row is locked via
                                ``SELECT ... FOR UPDATE`` so the count →
                                cap → INSERT trio cannot interleave; a
                                concurrent INSERT that still trips
                                ``uq_party_participant`` is converted to a
                                clean ``already_joined`` return inside a
                                SAVEPOINT.
  * ``leave_party``           — keyed DELETE is naturally idempotent if the
                                row vanished concurrently, unlike a
                                ``session.delete()`` on a stale instance.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select

from core.security import hash_password
from models.portal.event import (
    SeasonalEvent,
    SeasonalProgress,
    WatchPartyParticipant,
)
from models.portal.profile import UserProfile
from models.user import User
from services.portal import events as events_mod
from services.portal.events import (
    create_watch_party,
    join_party,
    leave_party,
    update_event_progress,
)


async def _make_user(db, *, username: str) -> User:
    user = User(
        username=username,
        hashed_password=hash_password("EventsRacePassword123!"),
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
    db, *, target_count: int = 3, name: str = "Spring Marathon",
) -> SeasonalEvent:
    now = datetime.now(timezone.utc)
    event = SeasonalEvent(
        name=name,
        description="",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
        target_count=target_count,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


# 1. update_event_progress: zero → first increment → repeated increments.


@pytest.mark.asyncio
async def test_update_event_progress_creates_row_from_zero(db_session):
    user = await _make_user(db_session, username="prog-zero")
    event = await _make_event(db_session, target_count=5)

    result = await update_event_progress(db_session, event.id, user.id)
    assert result == {"progress": 1, "completed": False}

    rows = (await db_session.execute(
        select(SeasonalProgress).where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].progress == 1
    assert rows[0].completed is False


@pytest.mark.asyncio
async def test_update_event_progress_two_consecutive_increments(db_session):
    user = await _make_user(db_session, username="prog-two")
    event = await _make_event(db_session, target_count=10)

    first = await update_event_progress(db_session, event.id, user.id)
    second = await update_event_progress(db_session, event.id, user.id)

    assert first == {"progress": 1, "completed": False}
    assert second == {"progress": 2, "completed": False}

    fresh = (await db_session.execute(
        select(SeasonalProgress)
        .where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.progress == 2
    assert fresh.completed is False


@pytest.mark.asyncio
async def test_update_event_progress_uses_db_value_not_stale_orm(db_session):
    """The atomic SQL increment must read the DB value, not an in-memory
    ORM snapshot — otherwise a concurrent peer's bump would be lost."""
    user = await _make_user(db_session, username="prog-stale")
    event = await _make_event(db_session, target_count=100)

    # Seed an existing progression at 5.
    db_session.add(SeasonalProgress(
        event_id=event.id, user_id=user.id, progress=5, completed=False,
    ))
    await db_session.commit()

    # Pre-load the row into the session identity map so its in-memory
    # ``progress`` is 5.
    cached = (await db_session.execute(
        select(SeasonalProgress).where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
    )).scalar_one()
    assert cached.progress == 5

    # Simulate a concurrent peer bumping progress to 50 in the DB,
    # bypassing the session's identity map. ``synchronize_session=False``
    # leaves the cached ORM instance untouched at 5.
    from sqlalchemy import update as sa_update
    await db_session.execute(
        sa_update(SeasonalProgress)
        .where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
        .values(progress=50)
        .execution_options(synchronize_session=False)
    )
    await db_session.commit()
    assert cached.progress == 5, (
        "test pre-condition: cached row must remain stale at 5"
    )

    result = await update_event_progress(db_session, event.id, user.id)
    assert result["progress"] == 51, (
        "atomic UPDATE must use DB value (50 + 1 = 51), not stale ORM (5 + 1 = 6)"
    )

    fresh = (await db_session.execute(
        select(SeasonalProgress)
        .where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.progress == 51


@pytest.mark.asyncio
async def test_update_event_progress_savepoint_swallows_concurrent_insert(
    db_session, monkeypatch,
):
    """Force-exercise the IntegrityError → SAVEPOINT-rollback path on the
    initial INSERT.

    A real race is: peer A and peer B both read no row, both INSERT, one
    trips ``uq_seasonal_progress``. We reproduce this in a single process
    by:

    1. Pre-inserting the conflicting row (the "winning peer") at
       progress=2.
    2. Monkeypatching ``_load_seasonal_progress`` to return ``None`` so
       the call walks past the fast-path SELECT into the INSERT block.
    3. Calling ``update_event_progress`` — the INSERT must trip the unique
       constraint, the SAVEPOINT must roll back cleanly, and the call
       must transparently fall through to the atomic increment path.
    4. Verifying only one row exists, the progression bumped from 2 to 3,
       and the session is still usable via a sentinel write.

    Without the SAVEPOINT this test would surface a ``PendingRollback
    Error`` on the sentinel write, or leak the duplicate ``IntegrityError``.
    """
    user = await _make_user(db_session, username="prog-race")
    event = await _make_event(db_session, target_count=10)

    db_session.add(SeasonalProgress(
        event_id=event.id, user_id=user.id, progress=2, completed=False,
    ))
    await db_session.commit()

    async def _pretend_no_existing(_db, _event_id, _user_id):
        return None

    monkeypatch.setattr(
        events_mod, "_load_seasonal_progress", _pretend_no_existing,
    )

    # Must not raise — the IntegrityError is swallowed in the savepoint
    # and the existing row is updated transparently.
    result = await update_event_progress(db_session, event.id, user.id)
    assert result["progress"] == 3
    assert result["completed"] is False

    # Sentinel write proves the outer transaction stayed alive after the
    # savepoint rollback. Without the SAVEPOINT, this commit would
    # explode on the previously poisoned session.
    sentinel_user = await _make_user(db_session, username="prog-race-sentinel")
    db_session.add(SeasonalProgress(
        event_id=event.id, user_id=sentinel_user.id, progress=1, completed=False,
    ))
    await db_session.commit()

    rows = (await db_session.execute(
        select(SeasonalProgress).where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
    )).scalars().all()
    assert len(rows) == 1, "uq_seasonal_progress must keep exactly one row"
    assert rows[0].progress == 3


@pytest.mark.asyncio
async def test_update_event_progress_completed_flips_at_threshold_and_sticks(
    db_session,
):
    user = await _make_user(db_session, username="prog-complete")
    event = await _make_event(db_session, target_count=2)

    # 1st increment → 1/2, not completed.
    first = await update_event_progress(db_session, event.id, user.id)
    assert first == {"progress": 1, "completed": False}

    # 2nd increment hits the threshold → completed = True.
    second = await update_event_progress(db_session, event.id, user.id)
    assert second == {"progress": 2, "completed": True}

    # 3rd increment overshoots the threshold — completed must stay True.
    third = await update_event_progress(db_session, event.id, user.id)
    assert third == {"progress": 3, "completed": True}

    fresh = (await db_session.execute(
        select(SeasonalProgress)
        .where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.progress == 3
    assert fresh.completed is True


@pytest.mark.asyncio
async def test_update_event_progress_completed_in_one_shot(db_session):
    """When the very first increment already meets ``target_count``, the
    SAVEPOINT-protected initial INSERT must persist ``completed=True``."""
    user = await _make_user(db_session, username="prog-one-shot")
    event = await _make_event(db_session, target_count=1)

    result = await update_event_progress(db_session, event.id, user.id)
    assert result == {"progress": 1, "completed": True}

    fresh = (await db_session.execute(
        select(SeasonalProgress).where(
            SeasonalProgress.event_id == event.id,
            SeasonalProgress.user_id == user.id,
        )
    )).scalar_one()
    assert fresh.completed is True


# 2. join_party: cap enforcement, duplicate-race protection.


async def _make_party(db, host: User, *, max_participants: int = 5):
    """Create a watch party owned by ``host`` (host is auto-added as the
    first participant by ``create_watch_party``)."""
    res = await create_watch_party(db, host.id, {
        "title": "Race Night",
        "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=2),
        "max_participants": max_participants,
    })
    assert res["success"] is True
    return res["id"]


def _in_outer_transaction(db) -> bool:
    """Probe the underlying sync ``Session`` directly for transaction state.

    ``AsyncSession.in_transaction()`` proxies through SQLAlchemy machinery
    that, on this stack, can graze expired ORM attributes and surface a
    ``MissingGreenlet`` outside the async loop. Reading the sync session's
    public ``in_transaction()`` is a pure Python state check (it returns
    ``self._transaction is not None``) and is safe to call here.
    """
    return db.sync_session.in_transaction()


@pytest.mark.asyncio
async def test_join_party_full_when_host_already_fills_cap(db_session):
    host = await _make_user(db_session, username="party-host")
    joiner = await _make_user(db_session, username="party-joiner")
    # Capture the IDs up front: the rollback inside ``join_party`` expires
    # ORM instances, after which any attribute access on ``joiner`` would
    # trigger a sync lazy-load outside the async greenlet context.
    joiner_id = joiner.id
    party_id = await _make_party(db_session, host, max_participants=1)

    # Host already counted as the single participant.
    count = (await db_session.execute(
        select(func.count(WatchPartyParticipant.id))
        .where(WatchPartyParticipant.party_id == party_id)
    )).scalar()
    assert count == 1

    result = await join_party(db_session, party_id, joiner_id)
    assert result == {"error": "full"}

    # The FOR UPDATE row lock must be released before return — otherwise
    # under PostgreSQL the lock would survive on the session and stall
    # every parallel join. The session-level transaction state is the
    # observable proxy: a non-None outer transaction means the lock is
    # still held.
    assert _in_outer_transaction(db_session) is False, (
        "join_party (full) must release the FOR UPDATE lock before return"
    )

    # Joiner did not get inserted.
    rows = (await db_session.execute(
        select(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == joiner_id,
        )
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_join_party_not_found_releases_transaction(db_session):
    """A bogus ``party_id`` must still release whatever transaction the
    ``FOR UPDATE`` SELECT autobegan, even though no row was returned."""
    user = await _make_user(db_session, username="party-not-found")
    user_id = user.id

    result = await join_party(db_session, 9999, user_id)
    assert result == {"error": "not_found"}

    assert _in_outer_transaction(db_session) is False, (
        "join_party (not_found) must close the autobegun transaction"
    )

    # Sentinel write proves the session is immediately usable for follow-up.
    sentinel = await _make_user(
        db_session, username="party-not-found-sentinel",
    )
    assert sentinel.id is not None


@pytest.mark.asyncio
async def test_join_party_already_joined_pre_check_releases_transaction(
    db_session,
):
    """The duplicate pre-check (without monkeypatch) must release the
    ``FOR UPDATE`` row lock before returning ``already_joined``."""
    host = await _make_user(db_session, username="party-pre-host")
    joiner = await _make_user(db_session, username="party-pre-joiner")
    joiner_id = joiner.id
    party_id = await _make_party(db_session, host, max_participants=10)

    db_session.add(WatchPartyParticipant(party_id=party_id, user_id=joiner_id))
    await db_session.commit()

    result = await join_party(db_session, party_id, joiner_id)
    assert result == {"error": "already_joined"}

    assert _in_outer_transaction(db_session) is False, (
        "join_party (already_joined pre-check) must release the FOR UPDATE lock"
    )

    rows = (await db_session.execute(
        select(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == joiner_id,
        )
    )).scalars().all()
    assert len(rows) == 1, "duplicate pre-check must not insert a second row"


@pytest.mark.asyncio
async def test_join_party_savepoint_swallows_duplicate_race(
    db_session, monkeypatch,
):
    """Force-exercise the IntegrityError → SAVEPOINT-rollback path on a
    concurrent duplicate join.

    A real race is: peer A and peer B both pass the duplicate pre-check,
    both attempt INSERT, one trips ``uq_party_participant``. We reproduce
    this in a single process by:

    1. Pre-inserting the conflicting participant row.
    2. Monkeypatching ``_load_existing_participant`` to return ``None`` so
       the call walks past the duplicate pre-check into the INSERT block.
    3. Calling ``join_party`` — the INSERT must trip the unique
       constraint, the SAVEPOINT must roll back cleanly, and the call
       must return ``already_joined`` instead of leaking the IntegrityError.
    4. Verifying only one participant row exists and the session is still
       usable via a sentinel write.
    """
    host = await _make_user(db_session, username="party-race-host")
    joiner = await _make_user(db_session, username="party-race-joiner")
    joiner_id = joiner.id
    party_id = await _make_party(db_session, host, max_participants=10)

    db_session.add(WatchPartyParticipant(party_id=party_id, user_id=joiner_id))
    await db_session.commit()

    async def _pretend_no_existing(_db, _party_id, _user_id):
        return None

    monkeypatch.setattr(
        events_mod, "_load_existing_participant", _pretend_no_existing,
    )

    result = await join_party(db_session, party_id, joiner_id)
    assert result == {"error": "already_joined"}

    # The savepoint absorbed the duplicate IntegrityError, but the outer
    # transaction (which still held the FOR UPDATE row lock) must also
    # have been rolled back before return — otherwise the lock would
    # survive on the session under PostgreSQL.
    assert _in_outer_transaction(db_session) is False, (
        "join_party (duplicate race) must release the FOR UPDATE lock "
        "after swallowing the IntegrityError"
    )

    # Sentinel write proves the session is usable for fresh work after
    # the savepoint + outer rollback. Without the rollback, the FOR UPDATE
    # lock would still be held; without the SAVEPOINT, this commit would
    # explode on the previously poisoned session.
    sentinel = await _make_user(db_session, username="party-race-sentinel")
    sentinel_id = sentinel.id
    db_session.add(WatchPartyParticipant(party_id=party_id, user_id=sentinel_id))
    await db_session.commit()

    rows = (await db_session.execute(
        select(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == joiner_id,
        )
    )).scalars().all()
    assert len(rows) == 1, "uq_party_participant must keep exactly one row"


# 3. leave_party: idempotent when the row already vanished.


@pytest.mark.asyncio
async def test_leave_party_idempotent_when_row_already_gone(db_session):
    """If the participant row vanished concurrently between a caller's
    load and the actual DELETE, leave_party must still return success
    without raising ``IntegrityError`` or ``StaleDataError``.

    We reproduce that single-process by:

    1. Joining the party normally so a row exists.
    2. Issuing a raw keyed DELETE so the row is gone but a stale ORM
       instance might still claim to be persistent.
    3. Calling ``leave_party`` again — the keyed DELETE inside the
       function must affect 0 rows without raising, and the session must
       remain usable for follow-up writes.
    """
    host = await _make_user(db_session, username="leave-host")
    user = await _make_user(db_session, username="leave-user")
    party_id = await _make_party(db_session, host, max_participants=10)

    join_res = await join_party(db_session, party_id, user.id)
    assert join_res == {"success": True}

    # Wipe the row underneath the ORM via a raw keyed DELETE.
    await db_session.execute(
        sql_delete(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == user.id,
        )
    )
    await db_session.commit()

    result = await leave_party(db_session, party_id, user.id)
    assert result == {"success": True}

    # Sentinel write proves the session is still alive.
    sentinel = await _make_user(db_session, username="leave-sentinel")
    db_session.add(WatchPartyParticipant(party_id=party_id, user_id=sentinel.id))
    await db_session.commit()

    rows = (await db_session.execute(
        select(WatchPartyParticipant).where(
            WatchPartyParticipant.party_id == party_id,
            WatchPartyParticipant.user_id == user.id,
        )
    )).scalars().all()
    assert rows == []
