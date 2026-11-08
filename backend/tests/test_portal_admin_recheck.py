"""« Lancer la vérification » runs on every account that earns, and on those only."""
import pytest

from services.portal import achievements
from services.portal.admin_users_constants import SOURCE_LOCAL
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

RECHECK = "/api/portal/admin/debug/recheck-all-achievements"


@pytest.fixture
def checked(monkeypatch) -> list[int]:
    """Ids of the accounts the check ran on."""
    ids: list[int] = []

    async def spy(db, user_id, **kwargs):
        ids.append(user_id)
        return []

    monkeypatch.setattr(achievements, "safe_check_all_achievements", spy)
    return ids


@pytest.mark.asyncio
async def test_the_check_skips_only_the_accounts_that_no_longer_earn(client, db_session, checked):
    admin, _ = await make_portal_user(db_session, username="admin", role="admin")
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    alice, alice_profile = await make_portal_user(db_session, username="alice")
    bob, bob_profile = await make_portal_user(db_session, username="bob")
    alice_profile.account_active = False  # imported, never activated
    bob_profile.account_active = bob.is_active = False  # deactivated
    await db_session.commit()

    resp = await client.post(RECHECK)
    assert resp.status_code == 200, resp.text
    assert sorted(checked) == sorted([admin.id, alice.id])
    assert resp.json()["users_processed"] == 2


@pytest.mark.asyncio
async def test_the_check_skips_local_and_unlinked_accounts(client, db_session, checked):
    # The admin who runs it holds a local account, as on a real instance.
    admin, admin_profile = await make_portal_user(
        db_session, username="admin", role="admin", emby_user_id=None,
    )
    admin_profile.source = SOURCE_LOCAL
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    alice, _ = await make_portal_user(db_session, username="alice")
    await make_portal_user(db_session, username="bob", emby_user_id="")
    await make_portal_user(db_session, username="carol", emby_user_id=None)
    await db_session.commit()

    resp = await client.post(RECHECK)
    assert resp.status_code == 200, resp.text
    assert checked == [alice.id]
    assert resp.json()["users_processed"] == 1
