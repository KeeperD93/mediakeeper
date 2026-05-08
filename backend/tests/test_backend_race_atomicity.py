"""Race / atomicity hardening for three core write paths.

These tests run against the in-memory SQLite engine wired in ``conftest.py``.
SQLite serializes writes within the test event loop, so the goal here is
not to reproduce real cross-process contention — it is to lock down the
single-process invariants that the savepoint / row-lock changes were
introduced to preserve:

  * ``grant_xp``     — duplicate (user, action, reference) inserts must
                       leave the surrounding session usable, must not
                       wipe pending caller state, and must keep the
                       ``XpLedger`` / ``UserProfile`` counters honest.
  * ``pin_badge`` /
    ``unpin_badge`` — concurrent edits go through ``SELECT ... FOR
                       UPDATE`` so two passes that both see the same
                       ``selected_badges`` snapshot cannot stomp on each
                       other; the ``MAX_PINNED_BADGES`` cap, locked /
                       unlocked gating and idempotent unpin are
                       preserved.
  * ``maybe_blacklist_media`` — the select-then-insert window is now
                       wrapped in a SAVEPOINT so a duplicate is silently
                       ignored without rolling back any pending caller
                       work, and only one row ever lands per
                       ``(tmdb_id, media_type)``.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from core.security import hash_password
from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest, RequestBlacklist
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal.achievements_badges import pin_badge, unpin_badge
from services.portal.requests_blacklist import maybe_blacklist_media
from services.portal.xp import (
    DAILY_REQUEST_XP_CAP,
    XP_TABLE,
    grant_xp,
)


async def _make_profile(
    db,
    *,
    username: str = "racer",
    role: str = "viewer",
    xp: int = 0,
    level: int = 0,
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password=hash_password("RacerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role=role,
        account_active=True,
        xp=xp,
        level=level,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return user, profile


# 1. grant_xp: duplicate-insert path must NOT poison the caller's session.


@pytest.mark.asyncio
async def test_grant_xp_duplicate_keeps_session_usable_and_no_double_credit(
    db_session,
):
    user, profile = await _make_profile(db_session, username="xp-dup")

    first = await grant_xp(db_session, user.id, "request_created", "req-1")
    assert first is not None
    assert first["xp"] == XP_TABLE["request_created"]

    # Same (user, action, reference) — duplicate must be silently rejected.
    dup = await grant_xp(db_session, user.id, "request_created", "req-1")
    assert dup is None

    # The session is still alive: a follow-up read must succeed without
    # any "PendingRollbackError" / detached-instance fallout.
    ledger_count = (await db_session.execute(
        select(func.count(XpLedger.id)).where(
            XpLedger.user_id == user.id,
            XpLedger.action == "request_created",
            XpLedger.reference == "req-1",
        )
    )).scalar_one()
    assert ledger_count == 1, "duplicate XP grant must not insert a second row"

    # Profile XP was incremented exactly once.
    await db_session.refresh(profile)
    assert profile.xp == XP_TABLE["request_created"]


@pytest.mark.asyncio
async def test_grant_xp_two_distinct_references_stack(db_session):
    user, profile = await _make_profile(db_session, username="xp-stack")

    first = await grant_xp(db_session, user.id, "request_created", "req-1")
    second = await grant_xp(db_session, user.id, "request_created", "req-2")

    assert first is not None and second is not None
    expected = XP_TABLE["request_created"] * 2
    await db_session.refresh(profile)
    assert profile.xp == expected
    assert second["total_xp"] == expected


@pytest.mark.asyncio
async def test_grant_xp_request_created_daily_cap_still_enforced(db_session):
    """Saturate the ledger up to the cap and confirm the next grant returns
    ``None`` without writing a row — the savepoint refactor must not have
    weakened the daily cap on request XP."""
    user, profile = await _make_profile(db_session, username="xp-cap")

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Pre-seed enough request_created XP to hit the cap exactly.
    db_session.add(XpLedger(
        user_id=user.id,
        action="request_created",
        reference="seed-cap",
        xp=DAILY_REQUEST_XP_CAP,
        created_at=today_start,
    ))
    profile.xp = DAILY_REQUEST_XP_CAP
    db_session.add(profile)
    await db_session.commit()

    blocked = await grant_xp(db_session, user.id, "request_created", "req-over")
    assert blocked is None

    # No new XpLedger row was created.
    rows = (await db_session.execute(
        select(func.count(XpLedger.id)).where(
            XpLedger.user_id == user.id,
            XpLedger.action == "request_created",
        )
    )).scalar_one()
    assert rows == 1

    await db_session.refresh(profile)
    assert profile.xp == DAILY_REQUEST_XP_CAP


# 2. pin_badge / unpin_badge: locked vs unlocked, cap, idempotency.


async def _seed_unlocked_badges(
    db, user_id: int, count: int, *, prefix: str = "ach",
) -> list[str]:
    ids = []
    for i in range(count):
        ach_id = f"{prefix}-{i}"
        db.add(Achievement(
            id=ach_id,
            category="standard",
            name_key=f"{ach_id}.name",
            description_key=f"{ach_id}.desc",
            icon="trophy",
            tier=1,
            xp_reward=10,
            threshold=1,
            condition_type="manual",
        ))
        db.add(UserAchievement(
            user_id=user_id,
            achievement_id=ach_id,
            progress=1,
            unlocked=True,
            notified=True,
            unlocked_at=datetime.now(timezone.utc),
        ))
        ids.append(ach_id)
    await db.commit()
    return ids


@pytest.mark.asyncio
async def test_pin_badge_refuses_locked_achievement(db_session):
    user, _ = await _make_profile(db_session, username="pin-locked")
    db_session.add(Achievement(
        id="locked-ach",
        category="standard",
        name_key="locked.name",
        description_key="locked.desc",
        icon="lock",
        tier=1,
        xp_reward=10,
        threshold=1,
        condition_type="manual",
    ))
    db_session.add(UserAchievement(
        user_id=user.id,
        achievement_id="locked-ach",
        progress=0,
        unlocked=False,
        notified=False,
    ))
    await db_session.commit()

    ok = await pin_badge(db_session, user.id, "locked-ach")
    assert ok is False

    profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()
    assert (profile.selected_badges or []) == []


@pytest.mark.asyncio
async def test_pin_badge_caps_at_max_pinned_and_is_idempotent(db_session):
    user, _ = await _make_profile(db_session, username="pin-cap")
    ids = await _seed_unlocked_badges(db_session, user.id, 6)

    # Pin the first five — all succeed.
    for ach_id in ids[:5]:
        ok = await pin_badge(db_session, user.id, ach_id)
        assert ok is True

    profile = (await db_session.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert profile.selected_badges == ids[:5]

    # 6th pin must be refused (cap = 5).
    refused = await pin_badge(db_session, user.id, ids[5])
    assert refused is False

    profile = (await db_session.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert profile.selected_badges == ids[:5]

    # Re-pinning an already-pinned badge is idempotent — still True, list
    # unchanged, no duplicate.
    again = await pin_badge(db_session, user.id, ids[0])
    assert again is True
    profile = (await db_session.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert profile.selected_badges == ids[:5]


@pytest.mark.asyncio
async def test_unpin_badge_idempotent(db_session):
    user, _ = await _make_profile(db_session, username="unpin")
    [a, b] = await _seed_unlocked_badges(db_session, user.id, 2, prefix="up")

    assert await pin_badge(db_session, user.id, a) is True
    assert await pin_badge(db_session, user.id, b) is True

    # First unpin removes the badge.
    assert await unpin_badge(db_session, user.id, a) is True
    profile = (await db_session.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert profile.selected_badges == [b]

    # Second unpin on the same id is a no-op (still True).
    assert await unpin_badge(db_session, user.id, a) is True
    profile = (await db_session.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert profile.selected_badges == [b]


# 3. maybe_blacklist_media: idempotency, snapshot preserved on first insert.


async def _seed_three_rejections(
    db, *, tmdb_id: int = 4242, media_type: str = "movie",
) -> tuple[User, MediaRequest]:
    user, _ = await _make_profile(db, username=f"reqr-{tmdb_id}")
    last: MediaRequest | None = None
    for i in range(3):
        req = MediaRequest(
            user_id=user.id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            title="Test Title",
            year=2026,
            poster_url=None,
            status="rejected",
        )
        db.add(req)
        last = req
    await db.commit()
    assert last is not None
    await db.refresh(last)
    return user, last


@pytest.mark.asyncio
async def test_maybe_blacklist_first_call_inserts_with_requester_snapshot(
    db_session,
):
    requester, req = await _seed_three_rejections(db_session)
    admin, _ = await _make_profile(db_session, username="bl-admin", role="admin")

    await maybe_blacklist_media(db_session, req, admin.id)
    await db_session.commit()

    bl = (await db_session.execute(
        select(RequestBlacklist).where(
            RequestBlacklist.tmdb_id == req.tmdb_id,
            RequestBlacklist.media_type == req.media_type,
        )
    )).scalar_one()
    assert bl.reject_count == 3
    assert bl.blocked_by == admin.id
    assert bl.requesters and len(bl.requesters) == 1
    assert bl.requesters[0]["user_id"] == requester.id


@pytest.mark.asyncio
async def test_maybe_blacklist_second_call_is_idempotent(db_session):
    requester, req = await _seed_three_rejections(db_session, tmdb_id=4243)
    admin, _ = await _make_profile(db_session, username="bl-admin-2", role="admin")

    await maybe_blacklist_media(db_session, req, admin.id)
    await db_session.commit()

    # Second call must not raise IntegrityError and must not create a
    # second row. The session must remain usable for follow-up writes.
    await maybe_blacklist_media(db_session, req, admin.id)

    # Sentinel write proves the session is still alive after the
    # second (no-op) call — a leaked rollback would have detached this.
    sentinel = MediaRequest(
        user_id=requester.id,
        tmdb_id=99999,
        media_type="movie",
        title="Sentinel",
        status="pending",
    )
    db_session.add(sentinel)
    await db_session.commit()

    rows = (await db_session.execute(
        select(func.count(RequestBlacklist.id)).where(
            RequestBlacklist.tmdb_id == req.tmdb_id,
            RequestBlacklist.media_type == req.media_type,
        )
    )).scalar_one()
    assert rows == 1


@pytest.mark.asyncio
async def test_maybe_blacklist_savepoint_swallows_concurrent_insert(
    db_session, monkeypatch,
):
    """Force-exercise the IntegrityError → SAVEPOINT-rollback path.

    A real race would be: peer A and peer B both pass the
    ``is_media_blacklisted`` pre-check, both build the requester
    snapshot, both attempt the INSERT — one wins, the other trips
    ``uq_blacklist_media``. To reproduce that single-process, we:

    1. Pre-insert the conflicting row (the "winning peer").
    2. Monkeypatch ``is_media_blacklisted`` to return ``False`` so our
       call walks past the fast-path pre-check.
    3. Call ``maybe_blacklist_media`` — the INSERT must trip the unique
       constraint, the SAVEPOINT must roll back cleanly, and the call
       must return without raising.
    4. Verify the session is still usable, only one row exists, and the
       pre-existing snapshot was NOT overwritten.

    Without the SAVEPOINT this test would surface a ``PendingRollback
    Error`` on the sentinel write below, or leave the duplicate
    ``IntegrityError`` propagating out.
    """
    from services.portal import requests_blacklist as bl_mod

    _, req = await _seed_three_rejections(db_session, tmdb_id=4244)
    admin, _ = await _make_profile(db_session, username="bl-admin-3", role="admin")

    db_session.add(RequestBlacklist(
        tmdb_id=req.tmdb_id,
        media_type=req.media_type,
        title="Pre-existing",
        year=2026,
        requesters=[{"user_id": 999, "display_name": "ghost"}],
        reject_count=3,
        blocked_by=admin.id,
    ))
    await db_session.commit()

    async def _pretend_not_blacklisted(_db, _tmdb_id, _media_type):
        return False

    monkeypatch.setattr(
        bl_mod, "is_media_blacklisted", _pretend_not_blacklisted,
    )

    # Must not raise — the IntegrityError is swallowed in the savepoint.
    await maybe_blacklist_media(db_session, req, admin.id)

    # Sentinel write proves the outer transaction stayed alive after the
    # savepoint rollback. Without the SAVEPOINT, the failed INSERT would
    # poison the session and this commit would explode.
    sentinel = MediaRequest(
        user_id=admin.id,
        tmdb_id=88888,
        media_type="movie",
        title="Sentinel after race",
        status="pending",
    )
    db_session.add(sentinel)
    await db_session.commit()

    rows = (await db_session.execute(
        select(RequestBlacklist).where(
            RequestBlacklist.tmdb_id == req.tmdb_id,
            RequestBlacklist.media_type == req.media_type,
        )
    )).scalars().all()
    assert len(rows) == 1
    # The pre-existing snapshot must NOT have been overwritten.
    assert rows[0].requesters == [{"user_id": 999, "display_name": "ghost"}]
    assert rows[0].title == "Pre-existing"
