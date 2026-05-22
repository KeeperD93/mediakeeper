"""Snapshot tests for ``_collect_full_user_data``.

The helper is the source of truth for what we call "the user's data"
in MediaKeeper. The GDPR opt-in kickoff mandates 14 logical tables
(two of which collapse to existing ones) and explicitly excludes admin
curation fields (``admin_notes``, ``tags``).

These tests:

* Fail loudly if a table the spec promised disappears from the
  output dict (so a future refactor can't silently shrink the export).
* Verify the curation exclusions stay enforced.
* Verify own-only scoping for chat messages and list items so a user
  never sees another user's content in their own export.

The original kickoff used "watchlists" as a label; in MediaKeeper that
collapses to ``user_lists`` (already covered).
"""
from datetime import datetime

import pytest

from models.portal.chat import ChatMessage, ChatRoom
from models.portal.profile import UserProfile
from models.portal.social import (
    UserList,
    UserListItem,
    UserRating,
)
from models.user import User
from services.portal.gdpr import _collect_full_user_data


@pytest.mark.asyncio
async def test_collect_returns_every_table_promised_in_kickoff(db_session):
    """A regression guard on the table set: a missing key here means
    we silently dropped a table from the GDPR export."""
    user = User(username="u1", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(user_id=user.id, display_name="U1", role="viewer")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    out = await _collect_full_user_data(db_session, user, profile)

    expected_keys = {
        "metadata",
        "user_profile",
        "user_preferences",
        "user_lists",
        "user_list_items",
        "user_ratings",
        "user_achievements",
        "release_reminders",
        "chat_messages",
        "media_requests",
        "watch_party_participants",
        "user_login_history",
    }
    assert expected_keys.issubset(set(out.keys()))


@pytest.mark.asyncio
async def test_collect_excludes_admin_notes_and_tags_from_profile(db_session):
    """Admin curation fields must never reach a user-initiated export."""
    user = User(username="u2", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name="U2",
        role="viewer",
        admin_notes="private operator-only note",
        tags=["vip", "early-adopter"],
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    out = await _collect_full_user_data(db_session, user, profile)
    assert "admin_notes" not in out["user_profile"]
    assert "tags" not in out["user_profile"]


@pytest.mark.asyncio
async def test_chat_messages_are_strictly_own_only(db_session):
    """Every chat message in the export must belong to the requesting
    user; no other participant's content can leak."""
    me = User(username="me", hashed_password="x", is_active=True)
    other = User(username="other", hashed_password="x", is_active=True)
    db_session.add_all([me, other])
    await db_session.commit()
    await db_session.refresh(me)
    await db_session.refresh(other)

    me_profile = UserProfile(user_id=me.id, display_name="me", role="viewer")
    db_session.add(me_profile)
    room = ChatRoom(type="general", name="general")
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)

    db_session.add_all([
        ChatMessage(room_id=room.id, user_id=me.id, content="mine"),
        ChatMessage(room_id=room.id, user_id=other.id, content="not mine"),
    ])
    await db_session.commit()

    out = await _collect_full_user_data(db_session, me, me_profile)
    contents = [m["content"] for m in out["chat_messages"]]
    assert contents == ["mine"]


@pytest.mark.asyncio
async def test_user_list_items_only_my_lists_or_my_contributions(db_session):
    """Items live under list ownership; a foreign list's items must
    not appear unless the user added them as a collaborator."""
    me = User(username="me-l", hashed_password="x", is_active=True)
    other = User(username="other-l", hashed_password="x", is_active=True)
    db_session.add_all([me, other])
    await db_session.commit()
    await db_session.refresh(me)
    await db_session.refresh(other)
    me_profile = UserProfile(user_id=me.id, display_name="me-l", role="viewer")
    db_session.add(me_profile)
    await db_session.commit()
    await db_session.refresh(me_profile)

    my_list = UserList(user_id=me.id, name="My", privacy="private")
    other_list = UserList(user_id=other.id, name="Other", privacy="private")
    db_session.add_all([my_list, other_list])
    await db_session.commit()
    await db_session.refresh(my_list)
    await db_session.refresh(other_list)

    db_session.add_all([
        UserListItem(list_id=my_list.id, tmdb_id=1, media_type="movie",
                     added_by_user_id=me.id),
        UserListItem(list_id=other_list.id, tmdb_id=2, media_type="movie",
                     added_by_user_id=other.id),
        # Co-contribution: I added this on someone else's list.
        UserListItem(list_id=other_list.id, tmdb_id=3, media_type="movie",
                     added_by_user_id=me.id),
    ])
    await db_session.commit()

    out = await _collect_full_user_data(db_session, me, me_profile)
    tmdb_ids = sorted(item["tmdb_id"] for item in out["user_list_items"])
    assert tmdb_ids == [1, 3]


@pytest.mark.asyncio
async def test_user_ratings_scoped_to_owner(db_session):
    me = User(username="me-r", hashed_password="x", is_active=True)
    other = User(username="other-r", hashed_password="x", is_active=True)
    db_session.add_all([me, other])
    await db_session.commit()
    await db_session.refresh(me)
    await db_session.refresh(other)
    me_profile = UserProfile(user_id=me.id, display_name="me-r", role="viewer")
    db_session.add(me_profile)
    await db_session.commit()
    await db_session.refresh(me_profile)

    db_session.add_all([
        UserRating(user_id=me.id, tmdb_id=10, media_type="movie", rating=8),
        UserRating(user_id=other.id, tmdb_id=20, media_type="movie", rating=9),
    ])
    await db_session.commit()

    out = await _collect_full_user_data(db_session, me, me_profile)
    assert [r["tmdb_id"] for r in out["user_ratings"]] == [10]


@pytest.mark.asyncio
async def test_metadata_contains_user_id_username_and_iso_timestamp(db_session):
    user = User(username="meta-u", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(user_id=user.id, display_name="meta-u", role="viewer")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    out = await _collect_full_user_data(db_session, user, profile)
    md = out["metadata"]
    assert md["user_id"] == user.id
    assert md["username"] == "meta-u"
    # ISO 8601 round-trips through ``fromisoformat``.
    parsed = datetime.fromisoformat(md["exported_at"])
    assert parsed.tzinfo is not None
