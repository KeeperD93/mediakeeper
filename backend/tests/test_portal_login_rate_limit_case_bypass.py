"""Portal brute-force tracking must collapse username casing variants.

``backend.api.portal.auth.portal_login`` (the Emby-only
``/api/portal/auth/login`` entry point) keyed its per-username failure
counter off the raw input string, unlike ``backend.api.auth.login`` which
already normalises. An attacker could alternate ``PortalUser`` /
``PORTALUSER`` / ``portaluser`` to stay under ``FAIL_BLOCK_THRESHOLD`` on
every individual per-username key, weakening the DB-backed lockout on the
portal login path.

The fix normalises ``req.username`` (strip + lower) before every call to
``ensure_not_blocked`` / ``count_recent_failures`` / ``record_failure`` /
``record_attempt`` in the portal login handler, mirroring the admin login,
so all casing variants now resolve to a single rate-limit bucket.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.security import SecurityAttempt


@pytest.mark.asyncio
async def test_portal_failures_under_different_casings_share_one_bucket(
    client, db_session,
):
    """3 failed portal attempts using 3 distinct casings must collapse into
    a single lowercase per-username row family in ``security_attempts``."""
    with patch(
        "api.portal.auth.authenticate_emby_user",
        new=AsyncMock(return_value=None),
    ):
        for username_variant in ("PortalUser", "PORTALUSER", "portaluser"):
            resp = await client.post("/api/portal/auth/login", json={
                "username": username_variant,
                "password": "WrongPassword!",
            })
            assert resp.status_code == 401, (
                f"variant {username_variant!r} expected 401, "
                f"got {resp.status_code}"
            )

    failures = (await db_session.execute(
        select(SecurityAttempt).where(
            SecurityAttempt.success == 0,
            SecurityAttempt.scope == "portal",
        )
    )).scalars().all()
    assert len(failures) == 3
    assert {row.username for row in failures} == {"portaluser"}, (
        f"all 3 portal failures must collapse to lowercase 'portaluser', "
        f"got {[row.username for row in failures]}"
    )


@pytest.mark.asyncio
async def test_portal_4th_attempt_is_blocked_regardless_of_casing(
    client, db_session,
):
    """After 3 failed casing variants, the 4th attempt — even with yet
    another casing — must be rate-limited (429) by ``ensure_not_blocked``
    before the Emby cascade is reached."""
    with patch(
        "api.portal.auth.authenticate_emby_user",
        new=AsyncMock(return_value=None),
    ):
        for username_variant in ("PortalUser", "PORTALUSER", "portaluser"):
            resp = await client.post("/api/portal/auth/login", json={
                "username": username_variant,
                "password": "WrongPassword!",
            })
            assert resp.status_code == 401

        resp = await client.post("/api/portal/auth/login", json={
            "username": "PoRtAlUsEr",
            "password": "WrongPassword!",
        })
    assert resp.status_code == 429, (
        f"4th attempt with another casing must be blocked, "
        f"got {resp.status_code} {resp.json()!r}"
    )
