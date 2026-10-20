"""Auto-archiving of fulfilled media requests.

Covers the gating, the time-window predicate, the
``available_at IS NOT NULL`` guard against legacy rows, and that archiving
keeps every row (and its ``updated_at``) instead of deleting it.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.user import User
from services.portal.requests_cleanup import REQUESTS_AUTO_CLEANUP_KEY, archive_old_available_requests
from services.scheduler._handlers import _handler_cleanup_available_requests
from services.settings import set_setting


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


async def _archived_ids(db) -> set[int]:
    rows = await db.execute(
        select(MediaRequest.id).where(MediaRequest.archived_at.is_not(None))
    )
    return set(rows.scalars().all())


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [0, -5])
async def test_archive_disabled_when_days_not_positive(db_session, days):
    await _bootstrap_user(db_session, "owner_off")
    db_session.add(MediaRequest(
        tmdb_id=1,
        media_type="movie",
        title="Old Movie",
        status="available",
        available_at=_now() - timedelta(days=999),
    ))
    await db_session.commit()

    assert await archive_old_available_requests(db_session, days=days) == 0
    assert await _archived_ids(db_session) == set()


@pytest.mark.asyncio
async def test_archive_only_aged_available_rows(db_session):
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
    # Served long ago, then rejected: the status alone keeps it out.
    row_c = MediaRequest(
        user_id=user.id,
        tmdb_id=12,
        media_type="movie",
        title="C — rejected, old stamp",
        status="rejected",
        available_at=now - timedelta(days=10),
    )
    db_session.add_all([row_a, row_b, row_c])
    await db_session.commit()
    aged_id = row_a.id

    assert await archive_old_available_requests(db_session, days=7) == 1

    assert await _archived_ids(db_session) == {aged_id}
    total = (await db_session.execute(select(MediaRequest.id))).scalars().all()
    assert len(total) == 3  # archived, never deleted


@pytest.mark.asyncio
async def test_archive_skips_rows_with_null_available_at(db_session):
    """Rows that flipped to available without the stamp must never be
    archived — their age is unknown."""
    user = await _bootstrap_user(db_session, "owner_null")
    db_session.add(MediaRequest(
        user_id=user.id,
        tmdb_id=20,
        media_type="movie",
        title="Legacy available",
        status="available",
        available_at=None,
    ))
    await db_session.commit()

    assert await archive_old_available_requests(db_session, days=1) == 0
    assert await _archived_ids(db_session) == set()


@pytest.mark.asyncio
async def test_archive_keeps_updated_at_and_earlier_archives(db_session):
    """Archiving is not activity (weekly counters read ``updated_at``) and a
    request archived earlier keeps its original archive date."""
    user = await _bootstrap_user(db_session, "owner_keep")
    then = _now() - timedelta(days=30)
    earlier = _now() - timedelta(days=5)
    fresh = MediaRequest(
        user_id=user.id, tmdb_id=30, media_type="movie", title="To archive",
        status="available", available_at=then, updated_at=then,
    )
    done = MediaRequest(
        user_id=user.id, tmdb_id=31, media_type="movie", title="Already archived",
        status="available", available_at=then, archived_at=earlier,
    )
    db_session.add_all([fresh, done])
    await db_session.commit()
    fresh_id, done_id = fresh.id, done.id

    assert await archive_old_available_requests(db_session, days=7) == 1

    rows = {
        r.id: r for r in (await db_session.execute(
            select(MediaRequest.id, MediaRequest.updated_at, MediaRequest.archived_at)
        )).all()
    }
    assert rows[fresh_id].updated_at.replace(tzinfo=None) == then.replace(tzinfo=None)
    assert rows[done_id].archived_at.replace(tzinfo=None) == earlier.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_scheduled_task_archives_only_once_a_delay_is_set(db_session):
    """The task is on by default: until a delay is set it archives nothing."""
    user = await _bootstrap_user(db_session, "owner_task")
    db_session.add(MediaRequest(
        user_id=user.id, tmdb_id=40, media_type="movie", title="Served",
        status="available", available_at=_now() - timedelta(days=30),
    ))
    await db_session.commit()

    assert await _handler_cleanup_available_requests(db_session) == {
        "archived": 0, "skipped": "disabled",
    }

    await set_setting(db_session, REQUESTS_AUTO_CLEANUP_KEY, "7")
    assert await _handler_cleanup_available_requests(db_session) == {"archived": 1, "days": 7}
