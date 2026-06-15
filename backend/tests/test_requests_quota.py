"""Tests for services.portal.requests_quota et le bypass admin de create_request."""
import pytest

from services.portal.requests import create_request
from services.portal.requests_quota import (
    current_month,
    get_or_create_quota,
    get_user_quota,
)


@pytest.mark.asyncio
async def test_get_or_create_quota_creates_row_on_first_access(admin_user, db_session):
    quota = await get_or_create_quota(db_session, admin_user.id)

    assert quota is not None
    assert quota.user_id == admin_user.id
    assert quota.used == 0
    assert quota.month == current_month()


@pytest.mark.asyncio
async def test_get_user_quota_resets_used_on_new_month(admin_user, db_session):
    quota = await get_or_create_quota(db_session, admin_user.id)
    quota.month = "1970-01"
    quota.used = 42
    db_session.add(quota)
    await db_session.commit()

    snapshot = await get_user_quota(db_session, admin_user.id)

    assert snapshot["used"] == 0
    assert snapshot["month"] == current_month()


@pytest.mark.asyncio
async def test_create_request_admin_does_not_consume_quota(admin_user, db_session):
    quota = await get_or_create_quota(db_session, admin_user.id)
    quota.max_allowed = 1
    quota.used = 1  # Already at limit
    db_session.add(quota)
    await db_session.commit()

    result = await create_request(
        db_session,
        admin_user.id,
        {
            "tmdb_id": 123,
            "media_type": "movie",
            "title": "Admin Test",
            "year": 2026,
            "poster_url": None,
        },
        is_admin=True,
    )

    assert result.get("success") is True
    assert result["quota"] is None  # Admin: no quota info exposed

    refreshed = await get_or_create_quota(db_session, admin_user.id)
    assert refreshed.used == 1  # Counter NOT incremented for admin


@pytest.mark.asyncio
async def test_create_request_non_admin_returns_quota_info(admin_user, db_session):
    quota = await get_or_create_quota(db_session, admin_user.id)
    quota.unlimited = False
    quota.max_allowed = 5
    db_session.add(quota)
    await db_session.commit()

    result = await create_request(
        db_session,
        admin_user.id,
        {
            "tmdb_id": 456,
            "media_type": "movie",
            "title": "User Test",
            "year": 2026,
            "poster_url": None,
        },
        is_admin=False,
    )

    assert result.get("success") is True
    assert result["quota"] == {"used": 1, "max": 5}


@pytest.mark.asyncio
async def test_quota_defaults_expose_auto_mode_fields(admin_user, db_session):
    """A freshly created quota carries the auto-mode defaults and the public
    snapshot surfaces them (mode 'manual', bounds 2/15, never recomputed)."""
    quota = await get_or_create_quota(db_session, admin_user.id)
    assert quota.mode == "manual"
    assert quota.auto_min == 2
    assert quota.auto_max == 15
    assert quota.last_recomputed_at is None

    snapshot = await get_user_quota(db_session, admin_user.id)
    assert snapshot["mode"] == "manual"
    assert snapshot["auto_min"] == 2
    assert snapshot["auto_max"] == 15
    assert snapshot["last_recomputed_at"] is None


@pytest.mark.asyncio
async def test_create_request_non_admin_blocked_when_quota_exceeded(admin_user, db_session):
    quota = await get_or_create_quota(db_session, admin_user.id)
    quota.unlimited = False
    quota.max_allowed = 2
    quota.used = 2
    db_session.add(quota)
    await db_session.commit()

    result = await create_request(
        db_session,
        admin_user.id,
        {
            "tmdb_id": 789,
            "media_type": "movie",
            "title": "Blocked",
            "year": 2026,
            "poster_url": None,
        },
        is_admin=False,
    )

    assert result == {"error": "quota_exceeded"}
