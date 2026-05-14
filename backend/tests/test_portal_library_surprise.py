"""Surprise endpoint — rapid-click resilience after ORM rollback.

Two surprise clicks in the same second hit the ``uq_xp_user_action_ref``
unique constraint and trip an IntegrityError → rollback. The rollback
expires the ``user`` ORM instance even with ``expire_on_commit=False``;
post-fix the endpoint caches the id + username before any commit so
the background task can be scheduled without re-touching the session.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token, make_portal_user


async def _seed_user(db_session) -> str:
    user, _profile = await make_portal_user(
        db_session,
        username="surprise-clicker",
        display_name="Clicker",
        role="viewer",
    )
    return user.username


def _auth(client, username: str) -> None:
    client.cookies.set(PORTAL_COOKIE, portal_token(username))


@pytest.mark.asyncio
async def test_surprise_two_rapid_clicks_both_succeed(client, db_session):
    username = await _seed_user(db_session)
    _auth(client, username)

    with patch("services.portal.available.get_surprise_pool", return_value=[]):
        r1 = await client.get("/api/portal/library/surprise?kind=movie")
        assert r1.status_code == 200, r1.text

        r2 = await client.get("/api/portal/library/surprise?kind=movie")
        # Post-fix: the duplicate-ts insert is absorbed silently; no 500
        # leaks back to the caller.
        assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
async def test_surprise_schedules_background_task_with_scalar_args(client, db_session):
    """The background task must receive plain ``viewer_id`` /
    ``viewer_username`` values cached BEFORE the commit — never the
    ORM instance itself, which can be expired by the rollback path."""
    username = await _seed_user(db_session)
    _auth(client, username)

    called_args = []

    def _capture(uid, uname, action):
        called_args.append((uid, uname, action))

    with patch("services.portal.available.get_surprise_pool", return_value=[]), \
         patch(
            "api.portal.library.safe_check_all_achievements_in_new_session",
            side_effect=_capture,
         ):
        resp = await client.get("/api/portal/library/surprise?kind=movie")
        assert resp.status_code == 200, resp.text

    assert len(called_args) == 1
    uid, uname, action = called_args[0]
    assert isinstance(uid, int) and uid > 0
    assert uname == username
    assert action == "surprise_used"
