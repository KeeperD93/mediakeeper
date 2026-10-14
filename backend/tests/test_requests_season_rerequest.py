"""A served series can still miss seasons: a new season request goes through
despite the previous, already-available request, while an open request (or a
non-season request) is still refused as a duplicate."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.portal.request import MediaRequest
from models.user import User
from services.portal.requests_create import create_request

SERIES = 7000
NEW_SEASONS = [{"season": 2, "episodes": "all"}, {"season": 3, "episodes": "all"}]


async def _viewer(db) -> int:
    user = User(
        username="viewer",
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    return user.id


async def _existing(db, user_id: int, status: str) -> None:
    db.add(MediaRequest(
        user_id=user_id, tmdb_id=SERIES, media_type="tv", title="Show", status=status,
        requested_seasons=[{"season": 1, "episodes": "all"}],
    ))
    await db.commit()


def _ask(seasons: list | None) -> dict:
    return {"tmdb_id": SERIES, "media_type": "tv", "title": "Show", "requested_seasons": seasons}


@pytest.mark.asyncio
async def test_season_request_goes_through_after_a_served_request(db_session):
    user_id = await _viewer(db_session)
    await _existing(db_session, user_id, "available")

    result = await create_request(db_session, user_id, _ask(NEW_SEASONS))

    assert result["success"] is True
    rows = (await db_session.execute(
        select(MediaRequest.status, MediaRequest.requested_seasons).order_by(MediaRequest.id)
    )).all()
    new_status = "approved" if result["auto_approved"] else "pending"
    assert [r.status for r in rows] == ["available", new_status]
    assert rows[1].requested_seasons == NEW_SEASONS


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "approved"])
async def test_season_request_still_blocked_by_an_open_request(db_session, status):
    user_id = await _viewer(db_session)
    await _existing(db_session, user_id, status)

    assert await create_request(db_session, user_id, _ask(NEW_SEASONS)) == {"error": "already_requested"}


@pytest.mark.asyncio
async def test_whole_series_request_still_blocked_by_a_served_request(db_session):
    user_id = await _viewer(db_session)
    await _existing(db_session, user_id, "available")

    assert await create_request(db_session, user_id, _ask(None)) == {"error": "already_requested"}


@pytest.mark.asyncio
async def test_duplicate_check_copes_with_several_matching_requests(db_session):
    """A served request plus the open one asked afterwards both match a
    non-season request: still a clean duplicate refusal, not a crash."""
    user_id = await _viewer(db_session)
    await _existing(db_session, user_id, "available")
    await _existing(db_session, user_id, "pending")

    assert await create_request(db_session, user_id, _ask(None)) == {"error": "already_requested"}
