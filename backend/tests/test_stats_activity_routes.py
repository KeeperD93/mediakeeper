"""Functional route coverage for the activity display-filter endpoints
(GET /api/stats/activity/users and /minimap) — thin wrappers previously
exercised only at the service layer. Admin-gated via ``authed_client``.
"""
from datetime import datetime, timezone

import pytest

from models.playback_stats import PlaybackSession


@pytest.mark.asyncio
async def test_activity_users_route_lists_distinct_users(authed_client, db_session):
    db_session.add_all([
        PlaybackSession(
            id=1, session_key="s1", user_id="u1", user_name="Alice",
            item_id="m1", item_name="Film", item_type="Movie",
        ),
        PlaybackSession(
            id=2, session_key="s2", user_id="u2", user_name="Bob",
            item_id="m1", item_name="Film", item_type="Movie",
        ),
    ])
    await db_session.commit()

    r = await authed_client.get("/api/stats/activity/users")
    assert r.status_code == 200
    names = {u["name"] for u in r.json()}
    assert {"Alice", "Bob"} <= names


@pytest.mark.asyncio
async def test_activity_minimap_route_returns_recent_playback(authed_client, db_session):
    db_session.add(PlaybackSession(
        id=1, session_key="s1", user_id="u1", user_name="Alice",
        item_id="m1", item_name="Film", item_type="Movie",
        started_at=datetime.now(timezone.utc),
    ))
    await db_session.commit()

    r = await authed_client.get("/api/stats/activity/minimap")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1
