"""Atomicity contract for ``RequestQuota`` lazy-create + ``create_request``.

Covers RequestQuota lazy-create conflicts, create_request early-return
rollbacks, quota caps, and admin bypass.
"""
import pytest
from sqlalchemy import select

from models.portal.request import MediaRequest, RequestQuota
from services.portal import requests_quota as quota_module
from services.portal.requests import create_request
from services.portal.requests_quota import (
    current_month,
    get_or_create_quota,
)


async def _sentinel_write(db_session, user_id: int, tmdb_id: int) -> int:
    """Persist a throwaway ``MediaRequest`` to prove the session is
    still usable. Returns the new row id; callers can refresh+assert."""
    sentinel = MediaRequest(
        user_id=user_id,
        tmdb_id=tmdb_id,
        media_type="movie",
        title="sentinel",
        status="pending",
    )
    db_session.add(sentinel)
    await db_session.commit()
    await db_session.refresh(sentinel)
    return sentinel.id


@pytest.mark.asyncio
async def test_get_or_create_quota_handles_concurrent_insert(
    admin_user, db_session, monkeypatch
):
    """A real DB ``UNIQUE`` violation on ``user_id`` must be absorbed:
    the SAVEPOINT rolls back, the winning row is reloaded, the caller's
    session stays alive."""
    # Simulate the "winner" of the race by inserting the quota row
    # ahead of our call and committing it.
    winner = RequestQuota(user_id=admin_user.id, month=current_month())
    db_session.add(winner)
    await db_session.commit()
    await db_session.refresh(winner)
    winner_id = winner.id

    # Force the INSERT branch despite the row existing: only the first
    # ``_load_quota`` call returns ``None`` (the post-conflict reload
    # falls through to the real implementation, so we get the winner).
    real_loader = quota_module._load_quota
    calls = {"n": 0}

    async def _miss_first(db, user_id, *, lock_row=False):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return await real_loader(db, user_id, lock_row=lock_row)

    monkeypatch.setattr(quota_module, "_load_quota", _miss_first)

    quota = await quota_module.get_or_create_quota(
        db_session, admin_user.id, commit=False
    )

    assert quota is not None
    assert quota.user_id == admin_user.id
    assert quota.id == winner_id  # winner row reloaded, not duplicated
    assert calls["n"] == 2  # initial miss + reload after IntegrityError

    # Only one quota row exists — no duplicate sneaked through.
    rows = (
        await db_session.execute(
            select(RequestQuota).where(RequestQuota.user_id == admin_user.id)
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_session_usable_after_quota_creation_conflict(
    admin_user, db_session, monkeypatch
):
    """After the SAVEPOINT absorbs the conflict, the outer session must
    accept further writes and commits."""
    winner = RequestQuota(user_id=admin_user.id, month=current_month())
    db_session.add(winner)
    await db_session.commit()

    real_loader = quota_module._load_quota
    calls = {"n": 0}

    async def _miss_first(db, user_id, *, lock_row=False):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return await real_loader(db, user_id, lock_row=lock_row)

    monkeypatch.setattr(quota_module, "_load_quota", _miss_first)

    await quota_module.get_or_create_quota(db_session, admin_user.id, commit=False)

    sentinel_id = await _sentinel_write(db_session, admin_user.id, tmdb_id=9001)
    assert sentinel_id is not None


@pytest.mark.asyncio
async def test_quota_exceeded_releases_transaction(admin_user, db_session):
    """``quota_exceeded`` must rollback so a sentinel write from the
    same session still succeeds — proves the row lock / advisory locks
    are released."""
    user_id = admin_user.id  # capture before rollback expires the ORM object
    quota = await get_or_create_quota(db_session, user_id)
    quota.unlimited = False
    quota.max_allowed = 1
    quota.used = 1  # already at cap
    db_session.add(quota)
    await db_session.commit()

    result = await create_request(
        db_session,
        user_id,
        {
            "tmdb_id": 7001,
            "media_type": "movie",
            "title": "Capped",
            "year": 2026,
            "poster_url": None,
        },
        is_admin=False,
    )
    assert result == {"error": "quota_exceeded"}

    sentinel_id = await _sentinel_write(db_session, user_id, tmdb_id=7002)
    assert sentinel_id is not None


@pytest.mark.asyncio
async def test_already_requested_releases_transaction(admin_user, db_session):
    """``already_requested`` must rollback so the advisory locks acquired
    by ``_acquire_request_creation_locks`` aren't held past the return."""
    user_id = admin_user.id  # capture before rollback expires the ORM object
    existing = MediaRequest(
        user_id=user_id,
        tmdb_id=8001,
        media_type="movie",
        title="Already pending",
        status="pending",
    )
    db_session.add(existing)
    await db_session.commit()

    result = await create_request(
        db_session,
        user_id,
        {
            "tmdb_id": 8001,
            "media_type": "movie",
            "title": "Dup attempt",
            "year": 2026,
            "poster_url": None,
        },
        is_admin=False,
    )
    assert result == {"error": "already_requested"}

    sentinel_id = await _sentinel_write(db_session, user_id, tmdb_id=8002)
    assert sentinel_id is not None


@pytest.mark.asyncio
async def test_two_sequential_creates_respect_max_allowed(admin_user, db_session):
    """``max_allowed=1`` must be honoured under back-to-back creates:
    second call returns ``quota_exceeded`` and ``used`` stays at 1."""
    user_id = admin_user.id  # capture before rollback expires the ORM object
    quota = await get_or_create_quota(db_session, user_id)
    quota.unlimited = False
    quota.max_allowed = 1
    quota.used = 0
    db_session.add(quota)
    await db_session.commit()

    first = await create_request(
        db_session,
        user_id,
        {
            "tmdb_id": 6001,
            "media_type": "movie",
            "title": "First",
            "year": 2026,
            "poster_url": None,
        },
        is_admin=False,
    )
    assert first.get("success") is True
    assert first["quota"] == {"used": 1, "max": 1}

    second = await create_request(
        db_session,
        user_id,
        {
            "tmdb_id": 6002,
            "media_type": "movie",
            "title": "Second",
            "year": 2026,
            "poster_url": None,
        },
        is_admin=False,
    )
    assert second == {"error": "quota_exceeded"}

    refreshed = await get_or_create_quota(db_session, user_id)
    assert refreshed.used == 1  # cap not exceeded


@pytest.mark.asyncio
async def test_admin_still_bypasses_quota_after_atomic_fixes(admin_user, db_session):
    """Admin bypass must remain intact: two admin creates in a row
    don't move ``quota.used`` even when ``max_allowed=1``."""
    user_id = admin_user.id
    quota = await get_or_create_quota(db_session, user_id)
    quota.unlimited = False
    quota.max_allowed = 1
    quota.used = 0
    db_session.add(quota)
    await db_session.commit()

    for tmdb_id in (5001, 5002):
        result = await create_request(
            db_session,
            user_id,
            {
                "tmdb_id": tmdb_id,
                "media_type": "movie",
                "title": f"Admin #{tmdb_id}",
                "year": 2026,
                "poster_url": None,
            },
            is_admin=True,
        )
        assert result.get("success") is True
        assert result["quota"] is None  # admin: no quota envelope exposed

    refreshed = await get_or_create_quota(db_session, user_id)
    assert refreshed.used == 0  # admin path never touches the counter
