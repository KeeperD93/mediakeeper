"""Avatar resolution in the admin Stats → Users aggregator.

A custom MediaKeeper upload (``avatar_custom_path``) must take precedence
over the Emby-proxied ``avatar_url`` so the Users tab and the merge overlay
show the same photo as the leaderboard and the Top widgets. Before the fix
the Users aggregator only read ``avatar_url`` and silently fell back to the
Emby photo for users who had uploaded a custom one.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.user import User
from services.portal.avatars import avatar_public_url
from services.stats_aggregator.users import get_users_stats


async def _make_profile(
    db_session, *, username, emby_user_id, avatar_url=None, avatar_custom_path=None,
):
    user = User(
        username=username,
        hashed_password="x",
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
        emby_user_id=emby_user_id,
        avatar_url=avatar_url,
        avatar_custom_path=avatar_custom_path,
    )
    db_session.add(profile)
    await db_session.commit()
    return user, profile


def _session(*, user_id, user_name):
    return PlaybackSession(
        session_key=f"S-{user_id}",
        user_id=user_id,
        user_name=user_name,
        item_id="ITEM-1",
        item_name="Film",
        item_type="Movie",
        position_ticks=1000,
        last_seen_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_users_stats_custom_avatar_wins_over_emby_url(db_session):
    await _make_profile(
        db_session,
        username="custom",
        emby_user_id="EMBY-CUSTOM",
        avatar_url="https://emby.example/avatar/should-be-ignored.png",
        avatar_custom_path="myphoto.png",
    )
    await _make_profile(
        db_session,
        username="plain",
        emby_user_id="EMBY-PLAIN",
        avatar_url="/api/emby/user-image/EMBY-PLAIN",
    )
    db_session.add_all([
        _session(user_id="EMBY-CUSTOM", user_name="custom"),
        _session(user_id="EMBY-PLAIN", user_name="plain"),
    ])
    await db_session.commit()

    with patch(
        "services.stats_aggregator.users.get_active_media_source",
        new=AsyncMock(return_value=None),
    ):
        result = await get_users_stats(db_session)

    by_id = {u["user_id"]: u for u in result["users"]}
    # Custom upload wins over the stored Emby URL.
    assert by_id["EMBY-CUSTOM"]["avatar_url"] == avatar_public_url("myphoto.png")
    assert by_id["EMBY-CUSTOM"]["avatar_url"] == "/api/portal/avatars/myphoto.png"
    # No custom upload → the stored (Emby-proxied) URL passes through unchanged.
    assert by_id["EMBY-PLAIN"]["avatar_url"] == "/api/emby/user-image/EMBY-PLAIN"


@pytest.mark.asyncio
async def test_users_stats_emby_only_user_falls_back_to_emby_photo(db_session):
    # An Emby account that watched content but never created an MK profile
    # must still show its Emby-proxied photo (parity with the Top widgets /
    # Sessions / 24h strip) instead of a silhouette.
    db_session.add(_session(user_id="EMBY-NOPROFILE", user_name="ghost"))
    await db_session.commit()

    with patch(
        "services.stats_aggregator.users.get_active_media_source",
        new=AsyncMock(return_value=None),
    ):
        result = await get_users_stats(db_session)

    by_id = {u["user_id"]: u for u in result["users"]}
    assert by_id["EMBY-NOPROFILE"]["avatar_url"] == "/api/emby/user-image/EMBY-NOPROFILE"
