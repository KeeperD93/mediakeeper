"""A served request no longer blocks a new one: a series can still miss
seasons, and a title gone from Emby can be asked again. Only an open request,
or a whole-series request for a title Emby holds, is refused. A re-request
reuses the latest live rejection and keeps its poster when none is sent."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.request import MediaRequest
from services.portal.requests_create import create_request

SERIES = 7000
NEW_SEASONS = [{"season": 2, "episodes": "all"}, {"season": 3, "episodes": "all"}]


async def _existing(db, user_id: int, status: str) -> None:
    db.add(MediaRequest(
        user_id=user_id, tmdb_id=SERIES, media_type="tv", title="Show", status=status,
        requested_seasons=[{"season": 1, "episodes": "all"}],
    ))
    await db.commit()


def _ask(seasons: list | None) -> dict:
    return {"tmdb_id": SERIES, "media_type": "tv", "title": "Show", "requested_seasons": seasons}


@pytest.mark.asyncio
async def test_season_request_goes_through_after_a_served_request(db_session, make_user):
    """Emby holds the series (its first season): the missing ones can still
    be requested."""
    user_id = (await make_user("viewer")).id
    await _existing(db_session, user_id, "available")
    db_session.add(EmbyTmdbIndex(emby_item_id="EMBY-SHOW", tmdb_id=SERIES, media_type="tv"))
    await db_session.commit()

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
async def test_season_request_still_blocked_by_an_open_request(db_session, status, make_user):
    user_id = (await make_user("viewer")).id
    await _existing(db_session, user_id, status)

    assert await create_request(db_session, user_id, _ask(NEW_SEASONS)) == {"error": "already_requested"}


@pytest.mark.asyncio
async def test_whole_series_request_goes_through_once_the_served_one_left_emby(db_session, make_user):
    """Marked available by mistake, or removed from Emby since: the title can
    be requested again."""
    user_id = (await make_user("viewer")).id
    await _existing(db_session, user_id, "available")

    assert (await create_request(db_session, user_id, _ask(None)))["success"] is True


@pytest.mark.asyncio
async def test_whole_series_request_refused_while_emby_holds_it(db_session, make_user):
    user_id = (await make_user("viewer")).id
    await _existing(db_session, user_id, "available")
    db_session.add(EmbyTmdbIndex(emby_item_id="EMBY-SHOW", tmdb_id=SERIES, media_type="tv"))
    await db_session.commit()

    assert await create_request(db_session, user_id, _ask(None)) == {"error": "already_available"}


@pytest.mark.asyncio
async def test_duplicate_check_copes_with_several_matching_requests(db_session, make_user):
    """Two open requests both match a non-season request: still a clean
    duplicate refusal, not a crash."""
    user_id = (await make_user("viewer")).id
    await _existing(db_session, user_id, "approved")
    await _existing(db_session, user_id, "pending")

    assert await create_request(db_session, user_id, _ask(None)) == {"error": "already_requested"}


@pytest.mark.asyncio
async def test_re_request_with_two_live_rejections_reuses_the_latest(db_session, make_user):
    """Rejecting a served request can leave two live rejections for one title:
    the re-request reuses the latest one instead of crashing."""
    user_id = (await make_user("viewer")).id
    await _existing(db_session, user_id, "rejected")
    await _existing(db_session, user_id, "rejected")

    result = await create_request(db_session, user_id, _ask(None))

    assert result["success"] is True
    rows = (await db_session.execute(
        select(MediaRequest.id, MediaRequest.status, MediaRequest.retry_count).order_by(MediaRequest.id)
    )).all()
    assert rows[0].status == "rejected"
    assert (rows[1].id, rows[1].retry_count) == (result["id"], 1)


@pytest.mark.asyncio
async def test_re_request_without_a_poster_keeps_the_stored_one(db_session, make_user):
    poster = "https://image.tmdb.org/t/p/w300/p.jpg"
    user_id = (await make_user("viewer")).id
    db_session.add(MediaRequest(
        user_id=user_id, tmdb_id=SERIES, media_type="tv", title="Show", status="rejected",
        poster_url=poster,
    ))
    await db_session.commit()

    assert (await create_request(db_session, user_id, _ask(None)))["success"] is True
    assert (await db_session.execute(select(MediaRequest.poster_url))).scalar_one() == poster
