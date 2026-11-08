"""A failed trophy check costs its caller nothing: the shared session stays usable."""
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from constants.requests import REQUEST_PENDING
from constants.tmdb_media import TMDB_MEDIA_MOVIE
from models.playback_stats import PlaybackSession
from models.portal.achievement import UserAchievement
from models.portal.audit import AdminAuditLog
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.portal.social import PRIVACY_PUBLIC_READONLY
from services.portal import achievements
from services.portal.admin_users_constants import ACTION_DEBUG_ACHIEVEMENT_RECHECK_ALL
from services.portal.lists import create_list, update_list
from services.portal.lists_items import add_items
from services.portal.requests_fulfill import fulfill_open_requests
from services.stats_collector.collect import _grant_post_session_xp
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

RECHECK = "/api/portal/admin/debug/recheck-all-achievements"
TICK = 10_000_000


@pytest.fixture
def checks_fail(monkeypatch) -> list[int]:
    """Every check fails on a flush; lists the accounts whose check got that far,
    which a session left broken by the previous failure never does."""
    reached: list[int] = []

    async def standard(db, *, user_id, **_kwargs):
        reached.append(user_id)
        db.add(UserAchievement(user_id=user_id, achievement_id=None))  # a NOT NULL column
        await db.flush()

    monkeypatch.setattr(achievements, "check_standard", standard)
    return reached


async def _ids(db, *names: str) -> list[int]:
    return [(await make_portal_user(db, username=name))[0].id for name in names]


async def _closed_play(db, name: str, item: str) -> PlaybackSession:
    now = datetime.now(UTC)
    play = PlaybackSession(
        session_key=f"emby-{name}_{item}_1", user_id=f"emby-{name}", user_name=name,
        item_id=item, item_name="Test Movie", item_type="Movie",
        duration_ticks=7200 * TICK, position_ticks=7000 * TICK,
        started_at=now - timedelta(minutes=5), ended_at=now, is_active=False,
    )
    db.add(play)
    await db.commit()
    return play


@pytest.mark.asyncio
@pytest.mark.parametrize("silent", [True, False])
async def test_the_session_stays_usable_after_a_failed_check(db_session, checks_fail, silent):
    [alice_id] = await _ids(db_session, "alice")
    if silent:
        assert await achievements.safe_check_all_achievements(db_session, alice_id, "test") == []
    else:
        with pytest.raises(SQLAlchemyError):
            await achievements.safe_check_all_achievements(
                db_session, alice_id, "test", silent=False,
            )

    await db_session.execute(update(UserProfile).where(UserProfile.user_id == alice_id).values(xp=7))
    await db_session.commit()
    assert await db_session.scalar(select(UserProfile.xp).where(UserProfile.user_id == alice_id)) == 7
    assert checks_fail == [alice_id]


@pytest.mark.asyncio
@pytest.mark.parametrize("silent", [True, False])
async def test_a_failed_rollback_keeps_the_outcome_of_the_check(db_session, checks_fail, silent):
    [alice_id] = await _ids(db_session, "alice")
    rollback = db_session.rollback

    async def rollback_then_fail():
        await rollback()
        raise RuntimeError("Test rollback failure")

    with patch.object(db_session, "rollback", new=rollback_then_fail):
        if silent:
            assert await achievements.safe_check_all_achievements(db_session, alice_id, "test") == []
        else:
            # The check's own error, not the rollback's.
            with pytest.raises(SQLAlchemyError):
                await achievements.safe_check_all_achievements(
                    db_session, alice_id, "test", silent=False,
                )


@pytest.mark.asyncio
async def test_the_next_player_still_earns_watch_xp(db_session, checks_fail):
    ids = await _ids(db_session, "alice", "bob")
    plays = [await _closed_play(db_session, "alice", "movie-1"), await _closed_play(db_session, "bob", "movie-2")]

    await _grant_post_session_xp(db_session, plays)

    assert checks_fail == ids
    xp = dict((await db_session.execute(
        select(UserProfile.user_id, UserProfile.xp).where(UserProfile.user_id.in_(ids))
    )).all())
    assert xp[ids[0]] == xp[ids[1]] > 0


@pytest.mark.asyncio
async def test_the_recheck_runs_to_the_end_and_records_its_audit(client, db_session, checks_fail):
    admin, _ = await make_portal_user(db_session, username="admin", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    ids = [admin.id, *await _ids(db_session, "alice", "bob")]

    resp = await client.post(RECHECK)

    assert resp.status_code == 200, resp.text
    assert resp.json()["users_processed"] == 3
    assert sorted(checks_fail) == sorted(ids)
    payload = (await db_session.execute(
        select(AdminAuditLog.payload).where(AdminAuditLog.action == ACTION_DEBUG_ACHIEVEMENT_RECHECK_ALL)
    )).scalar_one()
    assert payload["users_processed"] == 3


@pytest.mark.asyncio
async def test_list_writes_succeed_although_their_check_fails(db_session, checks_fail):
    [alice_id] = await _ids(db_session, "alice")

    created = await create_list(db_session, alice_id, {"name": "Test List"})
    assert created["success"] is True
    list_id = created["id"]
    updated = await update_list(db_session, list_id, alice_id, {"privacy": PRIVACY_PUBLIC_READONLY})
    assert updated == {"success": True, "id": list_id, "changes": ["privacy"]}
    added = await add_items(db_session, list_id, alice_id, [
        {"tmdb_id": 12345, "media_type": TMDB_MEDIA_MOVIE, "title": "Test Movie"},
    ])
    assert added == {"success": True, "added": 1, "duplicates": 0}
    assert checks_fail == [alice_id] * 3


@pytest.mark.asyncio
async def test_every_requester_is_checked_although_a_check_fails(db_session, checks_fail):
    ids = await _ids(db_session, "alice", "bob")
    for tmdb_id, user_id in enumerate(ids, start=12345):
        db_session.add(MediaRequest(
            user_id=user_id, tmdb_id=tmdb_id, media_type=TMDB_MEDIA_MOVIE,
            title="Test Movie", status=REQUEST_PENDING,
        ))
        db_session.add(EmbyTmdbIndex(emby_item_id=f"emby-{tmdb_id}", tmdb_id=tmdb_id, media_type=TMDB_MEDIA_MOVIE))
    await db_session.commit()

    assert await fulfill_open_requests(db_session) == 2
    assert sorted(checks_fail) == sorted(ids)
