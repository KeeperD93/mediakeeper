"""« Lancer la vérification » runs on every account that earns, and on those only."""
import pytest

from services.portal import achievements
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

RECHECK = "/api/portal/admin/debug/recheck-all-achievements"


@pytest.mark.asyncio
async def test_the_check_skips_only_the_accounts_that_no_longer_earn(client, db_session, monkeypatch):
    admin, _ = await make_portal_user(db_session, username="admin", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    alice, alice_profile = await make_portal_user(db_session, username="alice")
    bob, bob_profile = await make_portal_user(db_session, username="bob")
    alice_profile.account_active = False  # imported, never activated
    bob_profile.account_active = bob.is_active = False  # deactivated
    await db_session.commit()
    checked: list[int] = []

    async def spy(db, user_id, user_name, **kwargs):
        checked.append(user_id)
        return []

    monkeypatch.setattr(achievements, "safe_check_all_achievements", spy)
    resp = await client.post(RECHECK)
    assert resp.status_code == 200, resp.text
    assert sorted(checked) == sorted([admin.id, alice.id])
    assert resp.json()["users_processed"] == 2
