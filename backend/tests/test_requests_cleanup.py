"""Auto-cleanup of fulfilled media requests.

Covers the gating, the time-window predicate, and the
``available_at IS NOT NULL`` guard against legacy rows.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.user import User
from services.portal.requests_cleanup import cleanup_old_available_requests


async def _bootstrap_user(db, username: str) -> User:
    user = User(
        username=username,
        hashed_password=hash_password("Irrelevant123!"),
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_cleanup_disabled_when_days_zero(db_session):
    await _bootstrap_user(db_session, "owner_zero")
    db_session.add(MediaRequest(
        tmdb_id=1,
        media_type="movie",
        title="Old Movie",
        status="available",
        available_at=_now() - timedelta(days=99),
    ))
    await db_session.commit()

    deleted = await cleanup_old_available_requests(db_session, days=0)
    assert deleted == 0
    remaining = (await db_session.execute(select(MediaRequest))).scalars().all()
    assert len(remaining) == 1


@pytest.mark.asyncio
async def test_cleanup_disabled_when_days_negative(db_session):
    await _bootstrap_user(db_session, "owner_neg")
    db_session.add(MediaRequest(
        tmdb_id=2,
        media_type="movie",
        title="Old Movie 2",
        status="available",
        available_at=_now() - timedelta(days=999),
    ))
    await db_session.commit()

    deleted = await cleanup_old_available_requests(db_session, days=-5)
    assert deleted == 0
    remaining = (await db_session.execute(select(MediaRequest))).scalars().all()
    assert len(remaining) == 1


@pytest.mark.asyncio
async def test_cleanup_deletes_only_aged_available_rows(db_session):
    user = await _bootstrap_user(db_session, "owner_window")
    now = _now()

    row_a = MediaRequest(
        user_id=user.id,
        tmdb_id=10,
        media_type="movie",
        title="A — aged available",
        status="available",
        available_at=now - timedelta(days=10),
    )
    row_b = MediaRequest(
        user_id=user.id,
        tmdb_id=11,
        media_type="movie",
        title="B — recent available",
        status="available",
        available_at=now - timedelta(days=2),
    )
    row_c = MediaRequest(
        user_id=user.id,
        tmdb_id=12,
        media_type="movie",
        title="C — pending, no stamp",
        status="pending",
        available_at=None,
    )
    db_session.add_all([row_a, row_b, row_c])
    await db_session.commit()
    aged_id, recent_id, pending_id = row_a.id, row_b.id, row_c.id

    deleted = await cleanup_old_available_requests(db_session, days=7)
    assert deleted == 1

    remaining_ids = {
        r.id for r in
        (await db_session.execute(select(MediaRequest))).scalars().all()
    }
    assert aged_id not in remaining_ids
    assert recent_id in remaining_ids
    assert pending_id in remaining_ids


@pytest.mark.asyncio
async def test_cleanup_skips_rows_with_null_available_at(db_session):
    """Legacy rows that flipped to available without the stamp (or rows
    never backfilled) must never be removed — their age is unknown."""
    user = await _bootstrap_user(db_session, "owner_null")
    row = MediaRequest(
        user_id=user.id,
        tmdb_id=20,
        media_type="movie",
        title="Legacy available",
        status="available",
        available_at=None,
    )
    db_session.add(row)
    await db_session.commit()
    row_id = row.id

    deleted = await cleanup_old_available_requests(db_session, days=1)
    assert deleted == 0
    survivor = (await db_session.execute(
        select(MediaRequest).where(MediaRequest.id == row_id)
    )).scalar_one_or_none()
    assert survivor is not None
