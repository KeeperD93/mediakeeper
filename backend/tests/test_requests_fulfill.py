"""Scheduled fulfilment of open media requests.

``fulfill_open_requests`` flips a pending / approved request to ``available``
once Emby holds what it asked for, independently of Discord notifications:
a movie as soon as the Emby <-> TMDB index has it, a series once every
requested episode that has already aired is in Emby.
"""
from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.event import MKNotification
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.user import User
from services.portal import requests_fulfill as fulfill
from services.scheduler._handlers import _handler_fulfill_requests
from services.scheduler._tasks import TASK_DEFINITIONS
from services.watchlist_scanner import _emby

AIRED = "2020-01-01"
UPCOMING = "2999-01-01"


async def _user(db, username: str) -> User:
    user = User(
        username=username,
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    db.add(UserProfile(user_id=user.id, display_name=username, role="viewer", account_active=True))
    await db.commit()
    return user


async def _request(
    db, user_id: int | None, tmdb_id: int, media_type: str = "movie", *,
    status: str = "pending", seasons: list | None = None, indexed: bool = True,
) -> MediaRequest:
    req = MediaRequest(
        user_id=user_id, tmdb_id=tmdb_id, media_type=media_type,
        title=f"Title {tmdb_id}", status=status, requested_seasons=seasons,
    )
    db.add(req)
    if indexed:
        db.add(EmbyTmdbIndex(emby_item_id=f"emby-{tmdb_id}", tmdb_id=tmdb_id, media_type=media_type))
    await db.commit()
    return req


async def _status(db, req_id: int) -> str:
    return (await db.execute(
        select(MediaRequest.status).where(MediaRequest.id == req_id)
    )).scalar_one()


async def _notifications(db, user_id: int) -> list[MKNotification]:
    return list((await db.execute(
        select(MKNotification).where(MKNotification.user_id == user_id)
    )).scalars().all())


@pytest.fixture
def checked(monkeypatch) -> list[int]:
    """Record the trophy re-checks instead of running the whole catalogue."""
    calls: list[int] = []

    async def fake_check(_db, *, user_id, user_name, source):
        calls.append(user_id)
        return []

    monkeypatch.setattr(fulfill, "safe_check_all_achievements", fake_check)
    return calls


def _library(monkeypatch, *, seasons: dict[int, list[tuple[int, str | None]]],
             present: set[tuple[int, int]], status: str = "Returning Series",
             ignored: list[str] | None = None) -> None:
    """Fake TMDB (season -> [(episode, air date)]) and the Emby episodes."""
    async def tmdb_series(_db, _tmdb_id):
        return {"status": status, "seasons": [{"season_number": n} for n in (0, *seasons)]}

    async def tmdb_season(_db, _tmdb_id, number):
        episodes = seasons.get(number)
        if episodes is None:
            return None
        return {"episodes": [{"episode_number": n, "air_date": d} for n, d in episodes]}

    async def emby_episodes(_db, _series_id, *, present_only=False):
        assert present_only
        return {key: [] for key in present}

    async def get_ignored(_db):
        return ignored or []

    monkeypatch.setattr(fulfill, "_tmdb_series", tmdb_series)
    monkeypatch.setattr(fulfill, "_tmdb_season", tmdb_season)
    monkeypatch.setattr(fulfill, "_get_emby_episodes", emby_episodes)
    monkeypatch.setattr(fulfill, "get_ignored", get_ignored)


def _aired(*numbers: int) -> list[tuple[int, str]]:
    return [(n, AIRED) for n in numbers]


@pytest.mark.asyncio
async def test_movie_in_library_is_served_and_notified(db_session, checked):
    user = await _user(db_session, "movie_fan")
    req = await _request(db_session, user.id, 4242)

    before = datetime.now(timezone.utc)
    assert await fulfill.fulfill_open_requests(db_session) == 1

    row = (await db_session.execute(
        select(MediaRequest).where(MediaRequest.id == req.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert row.status == "available"
    stamp = row.available_at
    if stamp.tzinfo is None:  # SQLite hands timezone-aware columns back naive.
        stamp = stamp.replace(tzinfo=timezone.utc)
    assert stamp >= before.replace(microsecond=0)
    notifs = await _notifications(db_session, user.id)
    assert [n.type for n in notifs] == ["request_available"]
    assert notifs[0].payload["request_id"] == req.id
    assert notifs[0].payload["tmdb_id"] == 4242
    assert checked == [user.id]


@pytest.mark.asyncio
async def test_movie_missing_from_library_stays_open(db_session, checked):
    user = await _user(db_session, "waiting_fan")
    req = await _request(db_session, user.id, 1111, indexed=False)

    assert await fulfill.fulfill_open_requests(db_session) == 0
    assert await _status(db_session, req.id) == "pending"
    assert await _notifications(db_session, user.id) == []
    assert checked == []


@pytest.mark.asyncio
async def test_second_run_does_not_notify_again(db_session, checked):
    user = await _user(db_session, "repeat_fan")
    await _request(db_session, user.id, 2020, status="approved")

    assert await fulfill.fulfill_open_requests(db_session) == 1
    assert await fulfill.fulfill_open_requests(db_session) == 0
    assert len(await _notifications(db_session, user.id)) == 1


@pytest.mark.asyncio
async def test_closed_requests_are_left_alone(db_session, checked):
    user = await _user(db_session, "closed_fan")
    rejected = await _request(db_session, user.id, 3001, status="rejected")
    served = await _request(db_session, user.id, 3002, status="available")

    assert await fulfill.fulfill_open_requests(db_session) == 0
    assert await _status(db_session, rejected.id) == "rejected"
    assert await _status(db_session, served.id) == "available"
    assert await _notifications(db_session, user.id) == []


@pytest.mark.asyncio
async def test_purged_requester_is_served_without_notification(db_session, checked):
    req = await _request(db_session, None, 5050)

    assert await fulfill.fulfill_open_requests(db_session) == 1
    assert await _status(db_session, req.id) == "available"
    assert (await db_session.execute(select(MKNotification))).scalars().all() == []
    assert checked == []


@pytest.mark.asyncio
async def test_episode_request_waits_for_every_requested_episode(db_session, checked, monkeypatch):
    user = await _user(db_session, "episode_fan")
    req = await _request(
        db_session, user.id, 7000, "tv", status="approved",
        seasons=[{"season": 2, "episodes": [8, 9, 10]}],
    )
    season_two = {2: _aired(*range(1, 11))}

    _library(monkeypatch, seasons=season_two, present={(2, n) for n in range(1, 10)})
    assert await fulfill.fulfill_open_requests(db_session) == 0
    assert await _status(db_session, req.id) == "approved"

    _library(monkeypatch, seasons=season_two, present={(2, n) for n in range(1, 11)})
    assert await fulfill.fulfill_open_requests(db_session) == 1
    assert await _status(db_session, req.id) == "available"
    assert len(await _notifications(db_session, user.id)) == 1


@pytest.mark.asyncio
async def test_episodes_not_aired_yet_are_not_awaited(db_session, checked, monkeypatch):
    user = await _user(db_session, "airing_fan")
    req = await _request(
        db_session, user.id, 7100, "tv", seasons=[{"season": 3, "episodes": "all"}],
    )
    _library(
        monkeypatch,
        seasons={3: [(1, AIRED), (2, AIRED), (3, UPCOMING), (4, None)]},
        present={(3, 1), (3, 2)},
    )

    assert await fulfill.fulfill_open_requests(db_session) == 1
    assert await _status(db_session, req.id) == "available"


@pytest.mark.asyncio
async def test_season_with_nothing_aired_stays_open(db_session, checked, monkeypatch):
    user = await _user(db_session, "early_fan")
    req = await _request(
        db_session, user.id, 7200, "tv", seasons=[{"season": 4, "episodes": "all"}],
    )
    _library(monkeypatch, seasons={4: [(1, UPCOMING), (2, UPCOMING)]}, present=set())

    assert await fulfill.fulfill_open_requests(db_session) == 0
    assert await _status(db_session, req.id) == "pending"


@pytest.mark.asyncio
async def test_whole_series_request_needs_every_aired_season(db_session, checked, monkeypatch):
    """No season detail means the whole series; the specials season is skipped
    (the fake has no TMDB data for it, so reading it would block the flip)."""
    user = await _user(db_session, "series_fan")
    req = await _request(db_session, user.id, 7300, "tv")
    seasons = {1: _aired(1, 2), 2: _aired(1, 2)}

    _library(monkeypatch, seasons=seasons, present={(1, 1), (1, 2)})
    assert await fulfill.fulfill_open_requests(db_session) == 0

    _library(monkeypatch, seasons=seasons, present={(1, 1), (1, 2), (2, 1), (2, 2)})
    assert await fulfill.fulfill_open_requests(db_session) == 1
    assert await _status(db_session, req.id) == "available"


@pytest.mark.asyncio
async def test_ended_series_awaits_episodes_without_air_date(db_session, checked, monkeypatch):
    user = await _user(db_session, "ended_fan")
    req = await _request(
        db_session, user.id, 7400, "tv", seasons=[{"season": 1, "episodes": "all"}],
    )
    seasons = {1: [(1, AIRED), (2, None)]}

    _library(monkeypatch, seasons=seasons, present={(1, 1)}, status="Ended")
    assert await fulfill.fulfill_open_requests(db_session) == 0

    _library(monkeypatch, seasons=seasons, present={(1, 1), (1, 2)}, status="Ended")
    assert await fulfill.fulfill_open_requests(db_session) == 1
    assert await _status(db_session, req.id) == "available"


@pytest.mark.asyncio
async def test_watchlist_ignored_episodes_count_as_present(db_session, checked, monkeypatch):
    user = await _user(db_session, "ignore_fan")
    req = await _request(
        db_session, user.id, 7500, "tv", seasons=[{"season": 1, "episodes": "all"}],
    )
    _library(
        monkeypatch, seasons={1: _aired(1, 2, 3)}, present={(1, 1), (1, 2)},
        ignored=["7500_s1_e3"],
    )

    assert await fulfill.fulfill_open_requests(db_session) == 1
    assert await _status(db_session, req.id) == "available"


@pytest.mark.asyncio
async def test_unreachable_tmdb_keeps_series_request_open(db_session, checked, monkeypatch):
    user = await _user(db_session, "offline_fan")
    req = await _request(db_session, user.id, 7600, "tv")
    _library(monkeypatch, seasons={1: _aired(1)}, present={(1, 1)})

    async def no_tmdb(_db, _tmdb_id):
        return None

    monkeypatch.setattr(fulfill, "_tmdb_series", no_tmdb)

    assert await fulfill.fulfill_open_requests(db_session) == 0
    assert await _status(db_session, req.id) == "pending"


@pytest.mark.asyncio
async def test_failed_flip_rolls_back_and_others_still_go_through(db_session, checked):
    """A notification failure undoes that flip only; the request is retried on
    the next run while the following ones are still served."""
    user = await _user(db_session, "atomic_fan")
    # Plain ids: the rollback expires the ORM objects of the test session.
    user_id = user.id
    first_id = (await _request(db_session, user_id, 8001)).id
    second_id = (await _request(db_session, user_id, 8002)).id
    real_create = fulfill.notif_svc.create
    failed: list[int] = []

    async def create_once_failing(db, notif_user_id, notif_type, payload):
        if not failed:
            failed.append(payload["request_id"])
            raise RuntimeError("bell offline")
        return await real_create(db, notif_user_id, notif_type, payload)

    with patch.object(fulfill.notif_svc, "create", side_effect=create_once_failing):
        assert await fulfill.fulfill_open_requests(db_session) == 1

    assert failed == [first_id]
    assert await _status(db_session, first_id) == "pending"
    assert await _status(db_session, second_id) == "available"
    assert [n.payload["request_id"] for n in await _notifications(db_session, user_id)] == [second_id]


@pytest.mark.asyncio
async def test_failed_trophy_check_does_not_stop_the_next_ones(db_session, monkeypatch):
    """The trophy wrapper keeps a failure to itself but not its failed
    transaction: each requester's check must start on a clean session."""
    for name, tmdb_id in (("first_fan", 8101), ("second_fan", 8102)):
        user = await _user(db_session, name)
        await _request(db_session, user.id, tmdb_id)
    calls: list[int] = []
    finished: list[int] = []

    async def check(db, *, user_id, user_name, source):
        calls.append(user_id)
        with suppress(Exception):  # the real wrapper logs and swallows the same way
            if len(calls) == 1:
                # A duplicate username: the flush fails mid-transaction.
                db.add(User(
                    username="first_fan", hashed_password="x",
                    is_active=True, must_change_password=False,
                ))
                await db.flush()
            await db.execute(select(1))
            finished.append(user_id)
        return []

    monkeypatch.setattr(fulfill, "safe_check_all_achievements", check)

    assert await fulfill.fulfill_open_requests(db_session) == 2
    assert len(calls) == 2
    assert finished == calls[1:]


@pytest.mark.parametrize(("raw", "expected"), [
    (None, None),
    ([], None),
    ([{"season": 1, "episodes": "all"}], {1: None}),
    ([{"season": 2, "episodes": [3, 4]}], {2: {3, 4}}),
    ([{"season": 2, "episodes": [3, {"bad": 1}, "4"]}], {2: {3}}),
    ([5], {5: None}),
    ([{"unexpected": True}], None),
])
def test_requested_episodes_reading(raw, expected):
    assert fulfill._requested_episodes(raw) == expected


@pytest.mark.asyncio
async def test_present_only_drops_emby_placeholders(monkeypatch):
    class _Response:
        status_code = 200

        @staticmethod
        def json():
            return {"Items": [
                {"ParentIndexNumber": 1, "IndexNumber": 1, "LocationType": "FileSystem"},
                {"ParentIndexNumber": 1, "IndexNumber": 2, "LocationType": "Virtual"},
            ]}

    class _Client:
        async def get(self, *_args, **_kwargs):
            return _Response()

    async def config(_db):
        return "http://emby.invalid", "key"

    monkeypatch.setattr(_emby, "_get_emby_config", config)
    monkeypatch.setattr(_emby, "get_internal_client", _Client)

    assert set(await _emby._get_emby_episodes(None, "series")) == {(1, 1), (1, 2)}
    assert set(await _emby._get_emby_episodes(None, "series", present_only=True)) == {(1, 1)}


@pytest.mark.asyncio
async def test_scheduled_task_reports_the_flips(monkeypatch):
    defn = TASK_DEFINITIONS["fulfill_requests"]
    assert defn["default_on"] is True
    assert defn["handler"] is _handler_fulfill_requests

    async def fake_fulfill(_db):
        return 3

    monkeypatch.setattr(fulfill, "fulfill_open_requests", fake_fulfill)
    assert await _handler_fulfill_requests(None) == {"fulfilled": 3}
