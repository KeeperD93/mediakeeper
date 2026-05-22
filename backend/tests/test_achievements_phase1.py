"""Phase-1 functional tests for the achievement runner.

Covers the five families that previously only refreshed at login (chat,
requests, tickets, avatar, events), the two new families (curator,
librarian), the placeholder sealing, and the admin debug helpers — all
through ``check_all_achievements`` to mirror what the wired triggers
will do at runtime.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.security import hash_password
from models.portal.achievement import Achievement, UserAchievement
from models.portal.chat import ChatMessage, ChatRoom
from models.portal.event import EventStatus, MKEvent
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.portal.social import (
    UserList,
    PRIVACY_PRIVATE,
    PRIVACY_PUBLIC_READONLY,
)
from models.portal.ticket import Ticket
from models.playback_stats import LibraryCache, PlaybackSession
from models.user import User
from services.portal import lists as lists_svc
from services.portal import lists_items as lists_items_svc
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements import (
    check_all_achievements,
    get_achievements_for_profile,
    safe_check_all_achievements,
    seed_achievements,
)
from services.portal.admin_debug import (
    admin_lock_achievement,
    admin_unlock_achievement,
)
from sqlalchemy import select


# ── Fixtures ────────────────────────────────────────────────────────────


async def _make_user_and_profile(
    db, username: str = "viewer", *, role: str = "viewer"
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username.title(),
        role=role,
        account_active=True,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return user, profile


async def _seed_chat_room(db) -> ChatRoom:
    room = ChatRoom(type="lobby", name="lobby")
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


async def _ach_unlocked(db, user_id: int, ach_id: str) -> bool:
    row = (await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == ach_id,
        )
    )).scalar_one_or_none()
    return bool(row and row.unlocked)


# ── 1. Smoke: empty catalogue ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_state_returns_no_unlocks(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    unlocks = await check_all_achievements(db_session, user.id)

    assert unlocks == []


# ── 2. Smoke: ten distinct watches unlock movie_buff_1 (Bronze = 10) ────


@pytest.mark.asyncio
async def test_ten_movie_plays_unlock_movie_buff_bronze(db_session):
    user, _ = await _make_user_and_profile(db_session)
    db_session.add(LibraryCache(lib_id="movies", name="Movies"))
    await db_session.commit()
    await seed_achievements(db_session)

    started = datetime(2026, 4, 11, 14, 0, tzinfo=timezone.utc)
    db_session.add_all([
        PlaybackSession(
            session_key=f"m{i}",
            user_id="emby-viewer",
            user_name=user.username,
            item_id=f"movie-{i}",
            item_name=f"Movie {i}",
            item_type="Movie",
            library_name="Movies",
            started_at=started + timedelta(hours=i),
            last_seen_at=started + timedelta(hours=i, minutes=120),
            ended_at=started + timedelta(hours=i, minutes=120),
            is_active=False,
        )
        for i in range(10)
    ])
    await db_session.commit()

    unlocks = await check_all_achievements(db_session, user.id, user.username)

    assert "movie_buff_1" in {u["achievement_id"] for u in unlocks}


# ── 3. Requester family ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_created_unlocks_requester_bronze(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    db_session.add(MediaRequest(
        user_id=user.id,
        tmdb_id=1234,
        media_type="movie",
        title="Movie X",
        status="pending",
    ))
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)

    assert await _ach_unlocked(db_session, user.id, "requester_1")


# ── 4. Reporter family ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ticket_created_unlocks_reporter_bronze(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    db_session.add(Ticket(
        user_id=user.id,
        media_title="Movie Y",
        media_type="movie",
        issue_type="audio",
        description="No 5.1 mix on this release.",
    ))
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)

    assert await _ach_unlocked(db_session, user.id, "reporter_1")


# ── 5. Chatty family ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fifty_chat_messages_unlock_chatty_bronze(db_session):
    user, _ = await _make_user_and_profile(db_session)
    room = await _seed_chat_room(db_session)
    await seed_achievements(db_session)

    db_session.add_all([
        ChatMessage(room_id=room.id, user_id=user.id, content=f"msg {i}")
        for i in range(50)
    ])
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)

    assert await _ach_unlocked(db_session, user.id, "chatty_1")


# ── 6. Photogenic family ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_avatar_set_unlocks_photogenic(db_session):
    user, profile = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    profile.avatar_url = "https://example.test/avatar.png"
    db_session.add(profile)
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)

    assert await _ach_unlocked(db_session, user.id, "photogenic_1")


# ── 7. Organizer family ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_event_created_unlocks_organizer_bronze(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    db_session.add(MKEvent(
        creator_user_id=user.id,
        title="Movie Night",
        kind="public",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "Solo"}],
        scheduled_at=datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc),
        status=EventStatus.SCHEDULED.value,
    ))
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)

    assert await _ach_unlocked(db_session, user.id, "organizer_1")


# ── 8. Curator unlocks on first public list ─────────────────────────────


@pytest.mark.asyncio
async def test_first_public_list_unlocks_curator_bronze(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    result = await lists_svc.create_list(
        db_session, user.id,
        {"name": "Best of 2025", "privacy": PRIVACY_PUBLIC_READONLY},
    )

    assert result.get("success") is True
    assert await _ach_unlocked(db_session, user.id, "curator_1")


# ── 9. Curator does NOT unlock for private lists ────────────────────────


@pytest.mark.asyncio
async def test_private_list_does_not_unlock_curator(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    await lists_svc.create_list(
        db_session, user.id,
        {"name": "My private notes", "privacy": PRIVACY_PRIVATE},
    )

    assert not await _ach_unlocked(db_session, user.id, "curator_1")


# ── 10. Librarian counts max items, not the sum across lists ────────────


@pytest.mark.asyncio
async def test_librarian_tracks_peak_per_list_not_total(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    # Two lists with 6 items each: total is 12 (≥ librarian_1 threshold of 10)
    # but the *max per list* is only 6, so librarian_1 must stay locked.
    for name in ("Watchlist A", "Watchlist B"):
        created = await lists_svc.create_list(
            db_session, user.id, {"name": name, "privacy": PRIVACY_PRIVATE},
        )
        await lists_items_svc.add_items(
            db_session, created["id"], user.id,
            [
                {"tmdb_id": i, "media_type": "movie", "title": f"M{i}"}
                for i in range(1, 7)
            ],
        )

    await check_all_achievements(db_session, user.id, user.username)

    assert not await _ach_unlocked(db_session, user.id, "librarian_1")

    # Push one of the lists to ten items: librarian_1 must now unlock.
    big_list = (await db_session.execute(select(UserList))).scalars().first()
    await lists_items_svc.add_items(
        db_session, big_list.id, user.id,
        [{"tmdb_id": i, "media_type": "movie", "title": f"X{i}"} for i in range(7, 13)],
    )

    assert await _ach_unlocked(db_session, user.id, "librarian_1")


# ── 11. Placeholders are hidden from the profile payload ────────────────


@pytest.mark.asyncio
async def test_placeholder_ids_excluded_from_profile_payload(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    payload = await get_achievements_for_profile(db_session, user.id)
    exposed_ids = {item["id"] for item in payload["items"]}

    # No placeholder leaks into the items list…
    assert PLACEHOLDER_IDS.isdisjoint(exposed_ids)
    # …and the headline counter only counts the visible rows.
    assert payload["total_count"] == len(payload["items"])

    # The placeholders still live in the catalogue (so legacy unlocks
    # are preserved) — the runner just ignores them.
    rows = (await db_session.execute(select(Achievement.id))).scalars().all()
    assert PLACEHOLDER_IDS.issubset(set(rows))


# ── 12. Admin unlock service is idempotent and reversible ──────────────


@pytest.mark.asyncio
async def test_admin_unlock_then_lock_then_unlock_is_idempotent(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    first = await admin_unlock_achievement(db_session, user.id, "movie_buff_1")
    assert first is not None
    assert first.get("unlocked") is True
    assert await _ach_unlocked(db_session, user.id, "movie_buff_1")

    # Calling unlock a second time is a no-op flagged by ``already``.
    second = await admin_unlock_achievement(db_session, user.id, "movie_buff_1")
    assert second.get("already") is True

    # Lock removes the row entirely so progression restarts cleanly.
    await admin_lock_achievement(db_session, user.id, "movie_buff_1")
    assert not await _ach_unlocked(db_session, user.id, "movie_buff_1")

    # And we can re-unlock from scratch without any persisted side effect
    # from the previous cycle.
    third = await admin_unlock_achievement(db_session, user.id, "movie_buff_1")
    assert third.get("unlocked") is True
    assert third.get("already") is False
    assert await _ach_unlocked(db_session, user.id, "movie_buff_1")


# ── 13. Wrapper logs the source and stays silent on success ─────────────


@pytest.mark.asyncio
async def test_safe_wrapper_runs_check_with_source_label(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    unlocks = await safe_check_all_achievements(
        db_session, user.id, user.username, source="manual_check", silent=False,
    )

    assert unlocks == []  # No data → no unlocks; no exception either.
