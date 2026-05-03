"""Slowapi 3/min/IP cap on the admin password reset endpoint.

Even though the route already requires ``get_current_user`` (backoffice
admin) plus the CSRF double-submit, a tighter cap matches the
sensitivity of the action — issuing a fresh plaintext password and
force-logging-out the target user. The cap is keyed on IP so two admins
on different boxes don't share the budget.
"""
from __future__ import annotations

import pytest

from models.portal.profile import UserProfile
from models.user import User
from core.security import hash_password


@pytest.mark.asyncio
async def test_reset_password_caps_at_three_per_minute(client, admin_user, db_session):
    """The 4th call within a minute returns 429."""
    # Open the backoffice session.
    r = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
    })
    assert r.status_code == 200, r.text

    # Seed a local user we can reset.
    target = User(
        username="resettable",
        hashed_password=hash_password("OldPassword123!"),
        is_active=True,
    )
    db_session.add(target)
    await db_session.commit()
    await db_session.refresh(target)

    profile = UserProfile(
        user_id=target.id,
        display_name="Resettable",
        role="viewer",
        account_active=True,
        source="local",
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    seen_codes: list[int] = []
    for _ in range(5):
        r = await client.post(f"/api/portal/admin/users/{profile.id}/reset-password")
        seen_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen_codes, f"expected 429 within 5 calls, saw {seen_codes}"
    successes = sum(1 for c in seen_codes if c == 200)
    assert successes <= 3, f"slowapi let through more than 3 successes: {successes}"
