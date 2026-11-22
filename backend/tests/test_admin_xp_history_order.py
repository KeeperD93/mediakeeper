"""XP history of the admin user drawer: date order and keyset paging."""
from datetime import datetime, timedelta, timezone

import pytest

from models.portal.xp_ledger import XpLedger
from services.portal.admin_users_feed import list_user_xp_ledger

_DAY = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)


async def _add(db, user_id, ref, at=None):
    """Insert one row and flush it, so ids follow the call order."""
    row = XpLedger(user_id=user_id, action="manual_grant", reference=ref, xp=10)
    if at is not None:
        row.created_at = at
    db.add(row)
    await db.flush()
    return row.id


async def _walk(db, user_id, limit):
    """Collect the ids page by page through the keyset cursor."""
    seen, cursor = [], None
    for _ in range(20):  # well above the rows of each test
        page = await list_user_xp_ledger(db, user_id, limit=limit, cursor=cursor)
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            return seen
    raise AssertionError("the cursor never ends")


@pytest.mark.asyncio
async def test_rows_written_late_are_listed_at_their_date(db_session, admin_user):
    # Written in this order, as a recalculation does: the last two are older.
    recent = await _add(db_session, admin_user.id, "recent", _DAY)
    old = await _add(db_session, admin_user.id, "old", _DAY - timedelta(days=20))
    middle = await _add(db_session, admin_user.id, "middle", _DAY - timedelta(days=5))
    await db_session.commit()

    for limit in (1, 2, 100):
        assert await _walk(db_session, admin_user.id, limit) == [recent, middle, old]


@pytest.mark.asyncio
async def test_paging_keeps_every_row_sharing_a_date(db_session, admin_user):
    # Two groups of equal dates: one written by Python, one by the server
    # default (whole seconds on SQLite, so a different text form).
    same = _DAY - timedelta(days=1)
    a = await _add(db_session, admin_user.id, "same-a", same)
    d1 = await _add(db_session, admin_user.id, "default-1")
    b = await _add(db_session, admin_user.id, "same-b", same)
    old = await _add(db_session, admin_user.id, "older", same - timedelta(days=1))
    d2 = await _add(db_session, admin_user.id, "default-2")
    c = await _add(db_session, admin_user.id, "same-c", same)
    await db_session.commit()

    for limit in (1, 2, 4):
        assert await _walk(db_session, admin_user.id, limit) == [d2, d1, c, b, a, old]
