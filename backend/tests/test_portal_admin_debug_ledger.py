"""Admin debug "set level" and the XP history: a change is kept with its sign,
and a level that leaves the XP total as it was adds no row."""
import pytest
from sqlalchemy import select

from models.portal.xp_ledger import XpLedger
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


async def _set_level(client, db_session, *, xp: int, level: int):
    admin, _ = await make_portal_user(db_session, username="admin", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    target, profile = await make_portal_user(db_session, username="alice")
    profile.xp = xp
    db_session.add(profile)
    await db_session.commit()

    resp = await client.post(
        "/api/portal/admin/debug/set-level", json={"user_id": target.id, "level": level},
    )
    assert resp.status_code == 200, resp.text
    rows = (await db_session.execute(
        select(XpLedger.xp).where(XpLedger.user_id == target.id)
    )).scalars().all()
    return resp.json(), rows


@pytest.mark.asyncio
async def test_set_level_keeps_the_signed_change(client, db_session):
    body, rows = await _set_level(client, db_session, xp=20, level=1)
    assert body == {"xp": 0, "level": 1, "delta": -20}
    assert rows == [-20]


@pytest.mark.asyncio
async def test_set_level_without_change_adds_no_row(client, db_session):
    body, rows = await _set_level(client, db_session, xp=0, level=1)
    assert body == {"xp": 0, "level": 1, "delta": 0}
    assert rows == []
