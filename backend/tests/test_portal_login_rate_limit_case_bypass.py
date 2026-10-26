"""Member brute-force tracking must collapse username casing variants.

The member path of ``/api/auth/portal-login`` keys its per-username
failure counter on the trimmed, lower-cased name, like the admin login.
Otherwise an attacker could alternate ``PortalUser`` / ``PORTALUSER`` /
``portaluser`` to stay under ``FAIL_BLOCK_THRESHOLD`` on every individual
per-username key, weakening the DB-backed lockout on member sign-ins.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete, select

from models.security import SecurityAttempt, SecurityBlock


@pytest.mark.asyncio
async def test_portal_failures_under_different_casings_share_one_bucket(
    client, db_session,
):
    """3 failed portal attempts using 3 distinct casings must collapse into
    a single lowercase per-username row family in ``security_attempts``."""
    with patch(
        "api.auth.login.authenticate_emby_user",
        new=AsyncMock(return_value=None),
    ):
        for username_variant in ("PortalUser", "PORTALUSER", "portaluser"):
            resp = await client.post("/api/auth/portal-login", json={
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
        "api.auth.login.authenticate_emby_user",
        new=AsyncMock(return_value=None),
    ):
        for username_variant in ("PortalUser", "PORTALUSER", "portaluser"):
            resp = await client.post("/api/auth/portal-login", json={
                "username": username_variant,
                "password": "WrongPassword!",
            })
            assert resp.status_code == 401

        # Only the name block may refuse now: the three failures also blocked the address.
        await db_session.execute(delete(SecurityBlock).where(SecurityBlock.username.is_(None)))
        await db_session.commit()

        resp = await client.post("/api/auth/portal-login", json={
            "username": "PoRtAlUsEr",
            "password": "WrongPassword!",
        })
    assert resp.status_code == 429, (
        f"4th attempt with another casing must be blocked, "
        f"got {resp.status_code} {resp.json()!r}"
    )
