"""Race / atomicity hardening for portal list-copy and social write paths.

These tests run against the in-memory SQLite engine wired in ``conftest.py``.
SQLite serialises writes within the test event loop, so we cannot reproduce
real cross-process contention — the goal is to lock down the single-process
invariants the savepoint / atomic-update changes were introduced to
preserve:

  * ``copy_list``           — ``UserList.copy_count`` is bumped through a
                              keyed SQL UPDATE so a stale identity-map
                              snapshot of ``src`` cannot silently overwrite
                              a concurrent peer's increment.
  * ``rate_media``          — the INSERT on ``uq_user_rating`` is wrapped
                              in a SAVEPOINT so a peer that beat us to the
                              same ``(user, tmdb, media_type)`` does not
                              poison the outer transaction; the call falls
                              back to updating the existing row.
  * ``toggle_rating_like``  — the INSERT on ``uq_rating_like`` is wrapped
                              in a SAVEPOINT so a concurrent like is a
                              silent idempotent add; the unlike branch
                              uses a keyed DELETE that is naturally
                              idempotent if the row vanished between the
                              load and here.
"""
from __future__ import annotations

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy import select, update

from core.security import hash_password
from models.portal.profile import UserProfile
from models.portal.social import (
    PRIVACY_PUBLIC_READONLY,
    UserList,
    UserListItem,
    UserRating,
    UserRatingLike,
)
from models.user import User
from services.portal import social as social_mod
from services.portal.lists_items import copy_list
from services.portal.social import rate_media, toggle_rating_like


async def _make_profile(
    db, *, username: str, role: str = "viewer",
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password=hash_password("RacerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role=role,
        account_active=True,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return user, profile


# 1. copy_list: copy_count must increment atomically.


@pytest.mark.asyncio
async def test_copy_list_two_consecutive_copies_increment_count_to_two(
    db_session,
):
    owner, _ = await _make_profile(db_session, username="cl-basic-owner")
    user_a, _ = await _make_profile(db_session, username="cl-basic-a")
    user_b, _ = await _make_profile(db_session, username="cl-basic-b")

    src = UserList(
        user_id=owner.id, name="Source list",
        privacy=PRIVACY_PUBLIC_READONLY, content_type="movies",
    )
    db_session.add(src)
    await db_session.commit()
    await db_session.refresh(src)
    src_id = src.id

    db_session.add(UserListItem(
        list_id=src_id, tmdb_id=42, media_type="movie",
        title="Test", added_by_user_id=owner.id,
    ))
    await db_session.commit()

    res_a = await copy_list(db_session, src_id, user_a.id)
    assert res_a["success"] is True
    assert res_a["items_copied"] == 1

    res_b = await copy_list(db_session, src_id, user_b.id)
    assert res_b["success"] is True
    assert res_b["items_copied"] == 1

    fresh = (await db_session.execute(
        select(UserList)
        .where(UserList.id == src_id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.copy_count == 2

    # Each copy ended up as a distinct private list with the source item.
    copies = (await db_session.execute(
        select(UserList).where(
            UserList.user_id.in_([user_a.id, user_b.id]),
            UserList.id != src_id,
        )
    )).scalars().all()
    assert len(copies) == 2
    for new_list in copies:
        items = (await db_session.execute(
            select(UserListItem).where(UserListItem.list_id == new_list.id)
        )).scalars().all()
        assert len(items) == 1
        assert items[0].tmdb_id == 42


@pytest.mark.asyncio
async def test_copy_list_increment_does_not_depend_on_stale_src(db_session):
    """The atomic SQL increment must use the DB value, not the in-memory
    ``src`` snapshot — otherwise a concurrent peer's bump would be lost."""
    owner, _ = await _make_profile(db_session, username="cl-stale-owner")
    other, _ = await _make_profile(db_session, username="cl-stale-other")

    src = UserList(
        user_id=owner.id, name="Stale Source",
        privacy=PRIVACY_PUBLIC_READONLY, content_type="movies",
        copy_count=5,
    )
    db_session.add(src)
    await db_session.commit()
    await db_session.refresh(src)
    src_id = src.id

    # Pre-load src into the session identity map. Its in-memory
    # ``copy_count`` is 5.
    cached = await db_session.get(UserList, src_id)
    assert cached.copy_count == 5

    # Simulate a concurrent peer bumping copy_count to 50 in the DB,
    # bypassing the session's identity map (``synchronize_session=False``
    # keeps the cached ORM instance untouched, so it stays stale at 5).
    await db_session.execute(
        update(UserList)
        .where(UserList.id == src_id)
        .values(copy_count=50)
        .execution_options(synchronize_session=False)
    )
    await db_session.commit()
    assert cached.copy_count == 5, (
        "test pre-condition: cached src must remain stale at 5"
    )

    # Now copy. The atomic UPDATE must read the DB value (50) and bump
    # to 51. A read-modify-write on ``src`` would have set 6 instead.
    result = await copy_list(db_session, src_id, other.id)
    assert result["success"] is True

    fresh = (await db_session.execute(
        select(UserList)
        .where(UserList.id == src_id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert fresh.copy_count == 51, (
        "atomic UPDATE must use DB value (50 + 1 = 51), not stale src (5 + 1 = 6)"
    )


# 2. rate_media: SAVEPOINT swallows uq_user_rating race.


@pytest.mark.asyncio
async def test_rate_media_first_call_creates_one_row(db_session):
    user, _ = await _make_profile(db_session, username="rate-first")

    result = await rate_media(
        db_session, user.id,
        {"tmdb_id": 100, "media_type": "movie", "rating": 8, "review": "Good"},
    )
    assert result["success"] is True

    rows = (await db_session.execute(
        select(UserRating).where(UserRating.user_id == user.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].rating == 8
    assert rows[0].review == "Good"


@pytest.mark.asyncio
async def test_rate_media_second_call_updates_in_place_no_duplicate(db_session):
    user, _ = await _make_profile(db_session, username="rate-update")

    await rate_media(
        db_session, user.id,
        {"tmdb_id": 200, "media_type": "movie", "rating": 5},
    )
    await rate_media(
        db_session, user.id,
        {"tmdb_id": 200, "media_type": "movie", "rating": 9, "review": "Better"},
    )

    rows = (await db_session.execute(
        select(UserRating).where(
            UserRating.user_id == user.id,
            UserRating.tmdb_id == 200,
            UserRating.media_type == "movie",
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].rating == 9
    assert rows[0].review == "Better"


@pytest.mark.asyncio
async def test_rate_media_savepoint_swallows_concurrent_insert(
    db_session, monkeypatch,
):
    """Force-exercise the IntegrityError → SAVEPOINT-rollback path.

    A real race is: peer A and peer B both pass the SELECT (no row), both
    attempt INSERT, one trips ``uq_user_rating``. We reproduce this in a
    single process by:

    1. Pre-inserting the conflicting row (the "winning peer").
    2. Monkeypatching ``_load_existing_rating`` to return ``None`` so the
       call walks past the fast-path SELECT and into the INSERT block.
    3. Calling ``rate_media`` — the INSERT must trip the unique
       constraint, the SAVEPOINT must roll back cleanly, and the call
       must transparently update the existing row.
    4. Verifying only one row exists, the rating was updated, the
       session is still usable via a sentinel write.

    Without the SAVEPOINT this test would surface a ``PendingRollback
    Error`` on the sentinel write, or leak the duplicate ``IntegrityError``.
    """
    user, _ = await _make_profile(db_session, username="rate-race")

    db_session.add(UserRating(
        user_id=user.id, tmdb_id=4242, media_type="movie",
        rating=10, review="winner",
    ))
    await db_session.commit()

    async def _pretend_no_existing(_db, _user_id, _tmdb_id, _media_type):
        return None

    monkeypatch.setattr(
        social_mod, "_load_existing_rating", _pretend_no_existing,
    )

    # Must not raise — the IntegrityError is swallowed in the savepoint
    # and the existing row is updated transparently.
    result = await rate_media(
        db_session, user.id,
        {"tmdb_id": 4242, "media_type": "movie", "rating": 5,
         "review": "loser updates"},
    )
    assert result["success"] is True

    # Sentinel write proves the outer transaction stayed alive after the
    # savepoint rollback. Without the SAVEPOINT, this commit would
    # explode on the previously poisoned session.
    db_session.add(UserRating(
        user_id=user.id, tmdb_id=99999, media_type="movie", rating=3,
    ))
    await db_session.commit()

    rows = (await db_session.execute(
        select(UserRating).where(
            UserRating.user_id == user.id,
            UserRating.tmdb_id == 4242,
            UserRating.media_type == "movie",
        )
    )).scalars().all()
    assert len(rows) == 1, "uq_user_rating must keep exactly one row"
    assert rows[0].rating == 5
    assert rows[0].review == "loser updates"


# 3. toggle_rating_like: SAVEPOINT on like, idempotent unlike.


async def _make_rating(db, user_id: int, tmdb_id: int) -> UserRating:
    rating = UserRating(
        user_id=user_id, tmdb_id=tmdb_id, media_type="movie", rating=8,
    )
    db.add(rating)
    await db.commit()
    await db.refresh(rating)
    return rating


@pytest.mark.asyncio
async def test_toggle_rating_like_first_call_creates_one_row(db_session):
    user, _ = await _make_profile(db_session, username="like-first")
    rating = await _make_rating(db_session, user.id, tmdb_id=11)

    result = await toggle_rating_like(db_session, rating.id, user.id)
    assert result == {"success": True, "action": "added"}

    rows = (await db_session.execute(
        select(UserRatingLike).where(UserRatingLike.rating_id == rating.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].user_id == user.id


@pytest.mark.asyncio
async def test_toggle_rating_like_savepoint_swallows_concurrent_like(
    db_session, monkeypatch,
):
    """Force-exercise the IntegrityError → SAVEPOINT-rollback path on a
    concurrent like.

    Choice documented here, not in a public doc: when two concurrent
    toggles starting from "no like" both INSERT, the loser's call also
    returns ``action="added"`` rather than ``"removed"``. Rationale: the
    user clicked "like" and the row count is exactly 1 afterwards, so the
    user-visible state matches their intent. Returning ``"removed"`` here
    would falsely tell the loser they had un-liked something — worse UX
    than the loser silently agreeing with the winner.
    """
    user, _ = await _make_profile(db_session, username="like-race")
    rating = await _make_rating(db_session, user.id, tmdb_id=22)

    db_session.add(UserRatingLike(rating_id=rating.id, user_id=user.id))
    await db_session.commit()

    async def _pretend_no_existing(_db, _rating_id, _user_id):
        return None

    monkeypatch.setattr(
        social_mod, "_load_existing_like", _pretend_no_existing,
    )

    result = await toggle_rating_like(db_session, rating.id, user.id)
    assert result == {"success": True, "action": "added"}

    # Sentinel write proves the outer transaction stayed alive.
    db_session.add(UserRating(
        user_id=user.id, tmdb_id=88888, media_type="movie", rating=4,
    ))
    await db_session.commit()

    rows = (await db_session.execute(
        select(UserRatingLike).where(UserRatingLike.rating_id == rating.id)
    )).scalars().all()
    assert len(rows) == 1, "uq_rating_like must keep exactly one row"


@pytest.mark.asyncio
async def test_toggle_rating_like_unlike_when_row_already_gone(
    db_session, monkeypatch,
):
    """If the like row vanished concurrently between load and delete, the
    unlike branch must still return success without raising
    ``IntegrityError`` or ``StaleDataError``.

    We force this state by:

    1. Inserting a like, refreshing the in-memory instance.
    2. Issuing a raw keyed DELETE so the DB row is gone but the session's
       identity-map instance still claims to be persistent.
    3. Monkeypatching ``_load_existing_like`` to hand back that stale
       instance.
    4. Calling ``toggle_rating_like`` — the keyed DELETE inside the
       function must affect 0 rows without raising.
    """
    user, _ = await _make_profile(db_session, username="like-gone")
    rating = await _make_rating(db_session, user.id, tmdb_id=33)

    like = UserRatingLike(rating_id=rating.id, user_id=user.id)
    db_session.add(like)
    await db_session.commit()
    await db_session.refresh(like)
    captured = like

    await db_session.execute(
        sql_delete(UserRatingLike).where(UserRatingLike.id == like.id)
    )
    await db_session.commit()

    async def _return_stale(_db, _rating_id, _user_id):
        return captured

    monkeypatch.setattr(social_mod, "_load_existing_like", _return_stale)

    result = await toggle_rating_like(db_session, rating.id, user.id)
    assert result == {"success": True, "action": "removed"}

    # Sentinel write proves the session is still alive.
    db_session.add(UserRating(
        user_id=user.id, tmdb_id=77777, media_type="movie", rating=2,
    ))
    await db_session.commit()

    rows = (await db_session.execute(
        select(UserRatingLike).where(UserRatingLike.rating_id == rating.id)
    )).scalars().all()
    assert len(rows) == 0
