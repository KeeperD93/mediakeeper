"""Anonymous display-name alias on user-facing portal endpoints.

Privacy boundary (Rules §22): when a viewer hits a user-to-user surface
(leaderboard, public profile, user picker) for an account that has not
picked its portal pseudo yet, the response must surface the localized
anonymous alias instead of the auto-populated Emby username.
"""
from __future__ import annotations

import pytest

from services.portal._display_name import stable_user_tag
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


@pytest.mark.asyncio
async def test_leaderboard_surfaces_alias_for_unset_pseudo(client, db_session):
    """A user that has never picked a pseudo renders as ``Utilisateur 1234``
    on the monthly leaderboard, never as the raw Emby username."""
    me, mp = await make_portal_user(
        db_session,
        username="my_emby_login",  # value that MUST NOT leak
        must_set=True,
    )
    mp.xp = 100
    db_session.add(mp)
    await db_session.commit()

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard?limit=20")
    assert resp.status_code == 200
    items = resp.json()["items"]
    target = next((it for it in items if it["user_id"] == me.id), None)
    assert target is not None
    expected_alias = f"Utilisateur {stable_user_tag(me.id)}"
    assert target["display_name"] == expected_alias
    assert target["display_name"] != "my_emby_login"


@pytest.mark.asyncio
async def test_leaderboard_keeps_real_pseudo_when_set(client, db_session):
    """Once the viewer-side user has picked a real pseudo, that value
    is returned verbatim — the alias path is only the fallback."""
    me, mp = await make_portal_user(
        db_session,
        username="my_emby_login",
        display_name="Alice",
        must_set=False,
    )
    mp.xp = 250
    db_session.add(mp)
    await db_session.commit()

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard?limit=20")
    assert resp.status_code == 200
    items = resp.json()["items"]
    target = next((it for it in items if it["user_id"] == me.id), None)
    assert target is not None
    assert target["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_leaderboard_alias_localizes_to_english(client, db_session):
    """The viewer's ``Accept-Language`` header drives the alias prefix:
    ``Utilisateur 1234`` in FR, ``User 1234`` in EN."""
    me, mp = await make_portal_user(
        db_session, username="my_emby_login", must_set=True,
    )
    mp.xp = 100
    db_session.add(mp)
    await db_session.commit()

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get(
        "/api/portal/achievements/leaderboard?limit=20",
        headers={"accept-language": "en-US,en;q=0.9,fr;q=0.8"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    target = next((it for it in items if it["user_id"] == me.id), None)
    assert target is not None
    assert target["display_name"] == f"User {stable_user_tag(me.id)}"
