"""The users list tells an account never activated from a deactivated one."""
import pytest

from core.security import create_access_token
from tests._portal_profile_helpers import make_portal_user


@pytest.mark.asyncio
async def test_the_list_marks_only_deactivated_accounts(client, admin_user, db_session):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}))
    _, alice = await make_portal_user(db_session, username="alice")
    bob, bob_profile = await make_portal_user(db_session, username="bob")
    alice.account_active = False  # imported, never activated
    bob_profile.account_active = bob.is_active = False
    await db_session.commit()

    resp = await client.get("/api/portal/admin/users")
    assert resp.status_code == 200, resp.text
    rows = {row["username"]: row for row in resp.json()["items"]}
    assert (rows["alice"]["account_active"], rows["alice"]["deactivated"]) == (False, False)
    assert (rows["bob"]["account_active"], rows["bob"]["deactivated"]) == (False, True)
