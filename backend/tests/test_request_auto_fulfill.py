"""Auto-fulfillment of pending media requests when Emby reports a match.

Plugged into the added-media notification pipeline by
``services.notification_engine._request_fulfill``. These tests verify
the four contract guarantees:
  * Movies flip to ``available`` on first Emby presence.
  * TV series flip on the first episode (asymmetric with the Discord
    season-completion logic — that one is about template selection).
  * The flip is idempotent under repeated scans.
  * The status update + bell insertion are atomic (either both land or
    nothing changes).
"""
import pytest
from sqlalchemy import select
from unittest.mock import patch

from core.security import hash_password
from models.portal.event import MKNotification
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.user import User
from services.notification_engine._request_fulfill import try_auto_fulfill


async def _bootstrap_user(db, username):
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


@pytest.mark.asyncio
async def test_movie_request_marked_available_when_movie_added(db_session):
    user = await _bootstrap_user(db_session, "watcher_movie")
    req = MediaRequest(
        user_id=user.id,
        tmdb_id=4242,
        media_type="movie",
        title="Demo Movie",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()

    item = {
        "Type": "Movie",
        "Name": "Demo Movie",
        "ProviderIds": {"Tmdb": "4242"},
    }
    notified = await try_auto_fulfill(item, db_session)
    await db_session.commit()

    assert notified == user.id
    refreshed = (
        await db_session.execute(
            select(MediaRequest).where(MediaRequest.id == req.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.status == "available"


@pytest.mark.asyncio
async def test_series_request_fulfills_on_first_episode(db_session):
    user = await _bootstrap_user(db_session, "watcher_series")
    req = MediaRequest(
        user_id=user.id,
        tmdb_id=7777,
        media_type="tv",
        title="Demo Show",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()

    item = {
        "Type": "Episode",
        "Name": "Pilot",
        "SeriesProviderIds": {"Tmdb": "7777"},
        "ParentIndexNumber": 1,
        "IndexNumber": 1,
    }
    notified = await try_auto_fulfill(item, db_session)
    await db_session.commit()

    assert notified == user.id
    refreshed = (
        await db_session.execute(
            select(MediaRequest).where(MediaRequest.id == req.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.status == "available"


@pytest.mark.asyncio
async def test_auto_fulfill_creates_user_notification(db_session):
    user = await _bootstrap_user(db_session, "watcher_notif")
    req = MediaRequest(
        user_id=user.id,
        tmdb_id=1010,
        media_type="movie",
        title="Notif Movie",
        poster_url="poster.png",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()

    item = {
        "Type": "Movie",
        "Name": "Notif Movie",
        "ProviderIds": {"Tmdb": "1010"},
    }
    await try_auto_fulfill(item, db_session)
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(MKNotification).where(MKNotification.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    notif = rows[0]
    assert notif.type == "request_available"
    assert notif.payload["tmdb_id"] == 1010
    assert notif.payload["request_id"] == req.id


@pytest.mark.asyncio
async def test_auto_fulfill_is_idempotent(db_session):
    """A re-scan must not flip an already-available request a second time
    nor stack duplicate bell notifications."""
    user = await _bootstrap_user(db_session, "watcher_idem")
    req = MediaRequest(
        user_id=user.id,
        tmdb_id=2020,
        media_type="movie",
        title="Idempotent Movie",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()

    item = {
        "Type": "Movie",
        "Name": "Idempotent Movie",
        "ProviderIds": {"Tmdb": "2020"},
    }
    first = await try_auto_fulfill(item, db_session)
    await db_session.commit()
    second = await try_auto_fulfill(item, db_session)
    await db_session.commit()

    assert first == user.id
    assert second is None
    notifs = (
        await db_session.execute(
            select(MKNotification).where(MKNotification.user_id == user.id)
        )
    ).scalars().all()
    assert len(notifs) == 1


@pytest.mark.asyncio
async def test_auto_fulfill_atomic_on_notif_failure(db_session):
    """If the notif insert blows up, the status flip must roll back so
    the request stays ``pending`` on the next scan tick."""
    user = await _bootstrap_user(db_session, "watcher_atomic")
    req = MediaRequest(
        user_id=user.id,
        tmdb_id=3030,
        media_type="movie",
        title="Atomic Movie",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()
    req_id = req.id
    user_id = user.id

    item = {
        "Type": "Movie",
        "Name": "Atomic Movie",
        "ProviderIds": {"Tmdb": "3030"},
    }

    async def boom(*_args, **_kwargs):
        raise RuntimeError("notif backend offline")

    with patch(
        "services.notification_engine._request_fulfill.notif_svc.create",
        side_effect=boom,
    ):
        with pytest.raises(RuntimeError):
            await try_auto_fulfill(item, db_session)

    db_session.expire_all()
    refreshed = (
        await db_session.execute(
            select(MediaRequest).where(MediaRequest.id == req_id)
        )
    ).scalar_one()
    assert refreshed.status == "pending"
    notifs = (
        await db_session.execute(
            select(MKNotification).where(MKNotification.user_id == user_id)
        )
    ).scalars().all()
    assert notifs == []


@pytest.mark.asyncio
async def test_auto_fulfill_skips_when_no_match(db_session):
    user = await _bootstrap_user(db_session, "watcher_nomatch")
    req = MediaRequest(
        user_id=user.id,
        tmdb_id=9999,
        media_type="movie",
        title="Other Movie",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()

    item = {
        "Type": "Movie",
        "Name": "Unrelated",
        "ProviderIds": {"Tmdb": "1234"},
    }
    notified = await try_auto_fulfill(item, db_session)
    await db_session.commit()

    assert notified is None
    refreshed = (
        await db_session.execute(
            select(MediaRequest).where(MediaRequest.id == req.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.status == "pending"
