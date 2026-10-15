"""The admin request queue restores a missing poster or backdrop from TMDB
(requests created before the backdrop column, or whose image was dropped at
creation), keeps the images already stored and leaves complete rows alone."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.portal.request import MediaRequest
from models.user import User
from services.portal import requests as req_svc

POSTER = "https://image.tmdb.org/t/p/w300/p.jpg"
BACKDROP = "https://image.tmdb.org/t/p/w780/b.jpg"


async def _request(db, **images) -> MediaRequest:
    user = User(
        username="requester",
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
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
async def test_missing_poster_is_restored_and_stored(db_session, monkeypatch):
    await _request(db_session, backdrop_url=BACKDROP)
    calls = _tmdb(monkeypatch, {"poster": POSTER, "backdrop": "https://image.tmdb.org/t/p/w780/new.jpg"})

    out = await req_svc.list_requests(db_session, page=1, include_sensitive=True)

    assert calls == [("tv", 4242)]
    assert out["items"][0]["poster_url"] == POSTER
    assert out["items"][0]["backdrop_url"] == BACKDROP
    stored = (await db_session.execute(select(MediaRequest.poster_url))).scalar_one()
    assert stored == POSTER


@pytest.mark.asyncio
async def test_complete_rows_do_not_call_tmdb(db_session, monkeypatch):
    await _request(db_session, poster_url=POSTER, backdrop_url=BACKDROP)
    calls = _tmdb(monkeypatch, {"poster": "unused", "backdrop": "unused"})

    await req_svc.list_requests(db_session, page=1, include_sensitive=True)

    assert calls == []


@pytest.mark.asyncio
async def test_tmdb_failure_leaves_the_row_unchanged(db_session, monkeypatch):
    await _request(db_session)
    _tmdb(monkeypatch, {"error": "tmdb_detail_failed"})

    out = await req_svc.list_requests(db_session, page=1, include_sensitive=True)

    assert out["items"][0]["poster_url"] is None
    assert out["items"][0]["backdrop_url"] is None
