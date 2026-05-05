"""Lucky family unlock + Surprise overlay ledger tracking.

The four tiers (``lucky_1``..``lucky_4``) graduate from the
``surprise_used`` ledger action. The tests assert:

* the surprise endpoint writes one ``XpLedger`` row per call,
* the duplicate-burst safety net (same-second reference + unique
  constraint) keeps the count idempotent,
* ``check_all_achievements`` walks the threshold ladder correctly,
* and the family is no longer flagged as a placeholder.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import UniqueConstraint, select

from core.security import hash_password
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal.achievements import (
    check_all_achievements,
    seed_achievements,
)
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from tests._portal_profile_helpers import (
    PORTAL_COOKIE,
    make_portal_user,
    portal_token,
)


async def _make_viewer(db_session) -> User:
    user = User(
        username="lucky-viewer",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(UserProfile(
        user_id=user.id,
        display_name="Lucky Viewer",
        role="viewer",
        account_active=True,
    ))
    await db_session.commit()
    return user


def _seed_ledger(db_session, user_id: int, count: int) -> None:
    """Bulk-insert ``count`` distinct ``surprise_used`` ledger rows."""
    for idx in range(count):
        db_session.add(XpLedger(
            user_id=user_id,
            action="surprise_used",
            reference=f"surprise-{idx:04d}",
            xp=0,
        ))


@pytest.mark.asyncio
@pytest.mark.parametrize("clicks,expected", [
    (1, "lucky_1"),
    (5, "lucky_2"),
    (15, "lucky_3"),
    (30, "lucky_4"),
])
async def test_lucky_unlocks_at_threshold(db_session, clicks, expected):
    user = await _make_viewer(db_session)
    await seed_achievements(db_session)
    _seed_ledger(db_session, user.id, clicks)
    await db_session.commit()

    unlocks = await check_all_achievements(db_session, user.id)
    unlocked_ids = {row["achievement_id"] for row in unlocks}
    assert expected in unlocked_ids


@pytest.mark.asyncio
async def test_lucky_does_not_unlock_below_threshold(db_session):
    user = await _make_viewer(db_session)
    await seed_achievements(db_session)
    _seed_ledger(db_session, user.id, 4)
    await db_session.commit()

    unlocks = await check_all_achievements(db_session, user.id)
    unlocked_ids = {row["achievement_id"] for row in unlocks}
    assert "lucky_1" in unlocked_ids
    assert "lucky_2" not in unlocked_ids
    assert "lucky_3" not in unlocked_ids
    assert "lucky_4" not in unlocked_ids


def test_xp_ledger_unique_constraint_guards_surprise_duplicate_burst():
    """Two surprise clicks landing inside the same wall-clock second
    produce the same ``reference`` string. The dedup safety net is the
    ``uq_xp_user_action_ref`` unique constraint on ``XpLedger``: this
    test pins it so a future schema rename can't silently break the
    idempotency that ``surprise_pool`` relies on."""
    unique_names = {
        c.name for c in XpLedger.__table__.constraints
        if isinstance(c, UniqueConstraint)
    }
    assert "uq_xp_user_action_ref" in unique_names


@pytest.mark.asyncio
async def test_surprise_endpoint_writes_ledger_row(client, db_session):
    user, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    fake_pool = AsyncMock(return_value=[])
    with patch(
        "api.portal.library.avail_svc.get_surprise_pool", new=fake_pool,
    ):
        resp = await client.get(
            "/api/portal/library/surprise", params={"kind": "movie"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"items": []}

    rows = (await db_session.execute(
        select(XpLedger).where(
            XpLedger.user_id == user.id,
            XpLedger.action == "surprise_used",
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].xp == 0
    # Reference is the per-second ISO timestamp produced by the endpoint.
    assert rows[0].reference.endswith("Z")
    assert "T" in rows[0].reference


def test_lucky_no_longer_in_placeholder_set():
    for ach_id in ("lucky_1", "lucky_2", "lucky_3", "lucky_4"):
        assert ach_id not in PLACEHOLDER_IDS
