"""The admin request queue restores a missing poster or backdrop from TMDB
(requests created before the backdrop column, or whose image was dropped at
creation), keeps the images already stored and the update date, and leaves
complete rows alone."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select, update

from models.portal.request import MediaRequest
from services.portal import requests as req_svc
from services.portal.admin import get_admin_stats

POSTER = "https://image.tmdb.org/t/p/w300/p.jpg"
BACKDROP = "https://image.tmdb.org/t/p/w780/b.jpg"


async def _request(db, make_user, **images) -> MediaRequest:
    user = await make_user("requester")
    req = MediaRequest(
        user_id=user.id, tmdb_id=4242, media_type="tv", title="Show", status="approved", **images,
    )
    db.add(req)
    await db.commit()
    return req


def _tmdb(monkeypatch, detail: dict) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []

    async def get_media_detail(media_type, tmdb_id, db=None, locale=None):
        calls.append((media_type, tmdb_id))
        return detail

    monkeypatch.setattr("services.tmdb.get_media_detail", get_media_detail)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize(("stored", "missing", "column"), [
    ({"backdrop_url": BACKDROP}, POSTER, "poster_url"),
    ({"poster_url": POSTER}, BACKDROP, "backdrop_url"),
])
async def test_missing_image_is_restored_and_stored(db_session, monkeypatch, stored, missing, column, make_user):
    await _request(db_session, make_user, **stored)
    calls = _tmdb(monkeypatch, {
        "poster": POSTER if column == "poster_url" else "https://image.tmdb.org/t/p/w300/new.jpg",
        "backdrop": BACKDROP if column == "backdrop_url" else "https://image.tmdb.org/t/p/w780/new.jpg",
    })

    out = await req_svc.list_requests(db_session, page=1, include_sensitive=True)

    assert calls == [("tv", 4242)]
    assert out["items"][0]["poster_url"] == POSTER
    assert out["items"][0]["backdrop_url"] == BACKDROP
    row = (await db_session.execute(select(getattr(MediaRequest, column)))).scalar_one()
    assert row == missing


@pytest.mark.asyncio
async def test_filling_an_image_keeps_the_update_date(db_session, monkeypatch, make_user):
    """A filled-in image is not an edit: the queue's "this week" counters and
    its "modified" mention read updated_at."""
    req = await _request(db_session, make_user, backdrop_url=BACKDROP)
    long_ago = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await db_session.execute(
        update(MediaRequest).where(MediaRequest.id == req.id).values(updated_at=long_ago)
        .execution_options(synchronize_session="fetch")
    )
    await db_session.commit()
    _tmdb(monkeypatch, {"poster": POSTER})

    await req_svc.list_requests(db_session, page=1, include_sensitive=True)

    row = (await db_session.execute(select(MediaRequest.poster_url, MediaRequest.updated_at))).one()
    assert row.poster_url == POSTER
    assert row.updated_at.replace(tzinfo=timezone.utc) == long_ago  # SQLite reads it back naive
    assert (await get_admin_stats(db_session))["approved_this_week"] == 0


@pytest.mark.asyncio
async def test_a_status_change_made_while_tmdb_answers_is_kept(db_session, monkeypatch, make_user):
    """The queue page was loaded, then the request was rejected before the
    images came back: filling them must not bring back the loaded date."""
    req = await _request(db_session, make_user, backdrop_url=BACKDROP)
    rows = list((await db_session.execute(select(MediaRequest))).scalars().all())
    rejected_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    await db_session.execute(
        update(MediaRequest).where(MediaRequest.id == req.id)
        .values(status="rejected", updated_at=rejected_at)
        .execution_options(synchronize_session=False)  # the loaded row stays stale, as in another session
    )
    await db_session.commit()
    _tmdb(monkeypatch, {"poster": POSTER})

    await req_svc._backfill_images(db_session, rows)

    row = (await db_session.execute(
        select(MediaRequest.status, MediaRequest.poster_url, MediaRequest.updated_at)
    )).one()
    assert (row.status, row.poster_url) == ("rejected", POSTER)
    assert row.updated_at.replace(tzinfo=timezone.utc) == rejected_at
    assert rows[0].poster_url == POSTER


@pytest.mark.asyncio
async def test_complete_rows_do_not_call_tmdb(db_session, monkeypatch, make_user):
    await _request(db_session, make_user, poster_url=POSTER, backdrop_url=BACKDROP)
    calls = _tmdb(monkeypatch, {"poster": "unused", "backdrop": "unused"})

    await req_svc.list_requests(db_session, page=1, include_sensitive=True)

    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["error payload", "not a dict", "raises"])
async def test_tmdb_failure_leaves_the_row_unchanged(db_session, monkeypatch, answer, make_user):
    await _request(db_session, make_user)
    if answer == "raises":
        async def broken(*_args, **_kwargs):
            raise RuntimeError("tmdb offline")

        monkeypatch.setattr("services.tmdb.get_media_detail", broken)
    else:
        _tmdb(monkeypatch, {"error": "tmdb_detail_failed"} if answer == "error payload" else [])

    out = await req_svc.list_requests(db_session, page=1, include_sensitive=True)

    assert out["items"][0]["poster_url"] is None
    assert out["items"][0]["backdrop_url"] is None
