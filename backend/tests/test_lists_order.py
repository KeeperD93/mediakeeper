"""The order of a player's lists is the query's, never whatever the database hands back.

SQLite returns equal rows in insertion order anyway: only the query itself can show that
the tie is settled, which PostgreSQL does not do on its own once a row has been updated.
"""
import pytest
from sqlalchemy import event

from models.portal.social import PRIVACY_COLLABORATIVE, PRIVACY_PRIVATE, UserList, UserListContributor
from services.portal.lists_query import get_user_lists
from tests._portal_profile_helpers import make_portal_user


async def _lists_and_statements(db, user_id: int) -> tuple[list[str], list[str]]:
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.split()))

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        lists = await get_user_lists(db, user_id)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    return [row["name"] for row in lists], statements


@pytest.mark.asyncio
async def test_lists_of_the_same_rank_have_a_settled_order(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    db_session.add_all(
        UserList(user_id=alice.id, name=f"Mine {n}", privacy=PRIVACY_PRIVATE) for n in range(3)
    )
    shared = UserList(user_id=bob.id, name="Shared", privacy=PRIVACY_COLLABORATIVE)
    db_session.add(shared)
    await db_session.flush()
    db_session.add(UserListContributor(list_id=shared.id, user_id=alice.id))
    await db_session.commit()

    names, statements = await _lists_and_statements(db_session, alice.id)

    assert names == ["Mine 0", "Mine 1", "Mine 2", "Shared"]
    assert any(s.endswith("ORDER BY user_lists.sort_order, user_lists.id") for s in statements)
    assert any(s.endswith("ORDER BY user_lists.updated_at DESC, user_lists.id DESC") for s in statements)
