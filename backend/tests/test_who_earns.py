"""Who earns trophies and XP: an active account linked to the media server.

A deactivated account earns nothing, whatever path triggers the grant: a
served request, an admin's status change, a request filed on its behalf,
items added to its shared list. Nor does a local account, made in MediaKeeper
for its administration. Each case runs against an account that may earn too,
so the trigger is shown to pay."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from models.portal.achievement import UserAchievement
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.portal.social import PRIVACY_COLLABORATIVE, UserList, UserListContributor
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal import lists as lists_svc
from services.portal import lists_items
from services.portal.achievements import check_all_achievements, seed_achievements
from services.portal.requests_fulfill import fulfill_open_requests
from services.portal.xp import account_earns, grant_xp

ACTIVE = pytest.mark.parametrize("active", [True, False], ids=["active", "deactivated"])


async def _account(
    db, name: str, *, active: bool, role: str = "viewer", source: str = "emby",
) -> int:
    user = User(username=name, hashed_password="x", is_active=active, must_change_password=False)
    db.add(user)
    await db.flush()
    db.add(UserProfile(
        user_id=user.id, display_name=name, role=role, account_active=active, source=source,
    ))
    await db.commit()
    return user.id


async def _earned(db, user_id: int) -> tuple[int, int]:
    """Unlocked trophies and XP ledger rows of an account."""
    db.expire_all()
    trophies = await db.scalar(select(func.count()).select_from(UserAchievement).where(
        UserAchievement.user_id == user_id, UserAchievement.unlocked.is_(True),
    ))
    grants = await db.scalar(select(func.count()).select_from(XpLedger).where(XpLedger.user_id == user_id))
    return trophies, grants


def _assert_paid(earned: tuple[int, int], earns: bool) -> None:
    trophies, grants = earned
    if earns:
        assert trophies > 0 and grants > 0
    else:
        assert (trophies, grants) == (0, 0)


def _sign_in(client, username: str) -> None:
    client.cookies.set("rq_token", create_access_token({"sub": username, "scope": "portal"}))


@pytest.fixture
def background_on_test_db(monkeypatch, db_session):
    """Route triggers check trophies in a session of their own: open it on the test database."""
    monkeypatch.setattr(
        "core.database.AsyncSessionLocal",
        lambda: AsyncSession(db_session.bind, expire_on_commit=False),
    )


@pytest.mark.parametrize(("active", "source", "earns"), [
    (True, "emby", True),
    (False, "emby", False),
    (True, "local", False),
    (False, "local", False),
])
@pytest.mark.asyncio
async def test_only_an_active_media_server_account_earns(db_session, active, source, earns):
    alice = await _account(db_session, "alice", active=active, source=source)

    assert await account_earns(db_session, alice) is earns


@pytest.mark.asyncio
async def test_an_account_without_portal_profile_is_judged_by_its_activity(db_session):
    user = User(username="bob", hashed_password="x", is_active=True, must_change_password=False)
    db_session.add(user)
    await db_session.commit()

    assert await account_earns(db_session, user.id) is True
    assert await account_earns(db_session, 12345) is False


@ACTIVE
@pytest.mark.asyncio
async def test_the_trophy_check_pays_only_an_active_account(db_session, active):
    await seed_achievements(db_session)
    alice = await _account(db_session, "alice", active=active)
    db_session.add(MediaRequest(
        user_id=alice, tmdb_id=12345, media_type="movie", title="Test Movie", status="available",
    ))
    await db_session.commit()

    unlocks = await check_all_achievements(db_session, alice, "alice")

    assert bool(unlocks) is active
    _assert_paid(await _earned(db_session, alice), active)


@ACTIVE
@pytest.mark.asyncio
async def test_a_grant_pays_only_an_active_account(db_session, active):
    alice = await _account(db_session, "alice", active=active)

    grant = await grant_xp(db_session, alice, "request_created", "1")

    assert (grant is not None) is active
    assert (await _earned(db_session, alice))[1] == (1 if active else 0)


@ACTIVE
@pytest.mark.asyncio
async def test_a_served_request_pays_only_an_active_requester(db_session, active):
    await seed_achievements(db_session)
    alice = await _account(db_session, "alice", active=active)
    db_session.add(MediaRequest(
        user_id=alice, tmdb_id=12345, media_type="movie", title="Test Movie", status="pending",
    ))
    db_session.add(EmbyTmdbIndex(emby_item_id="emby-12345", tmdb_id=12345, media_type="movie"))
    await db_session.commit()

    assert await fulfill_open_requests(db_session) == 1

    _assert_paid(await _earned(db_session, alice), active)


@ACTIVE
@pytest.mark.asyncio
async def test_a_status_change_pays_only_an_active_requester(
    client, db_session, background_on_test_db, active,
):
    await seed_achievements(db_session)
    await _account(db_session, "admin_dm", active=True, role="admin")
    alice = await _account(db_session, "alice", active=active)
    request = MediaRequest(
        user_id=alice, tmdb_id=12345, media_type="movie", title="Test Movie", status="pending",
    )
    db_session.add(request)
    await db_session.commit()
    request_id = request.id

    _sign_in(client, "admin_dm")
    resp = await client.put(f"/api/portal/requests/{request_id}/status", json={"status": "approved"})

    assert resp.status_code == 200, resp.text
    _assert_paid(await _earned(db_session, alice), active)


@ACTIVE
@pytest.mark.asyncio
async def test_a_request_filed_on_behalf_pays_only_an_active_account(
    client, db_session, background_on_test_db, active,
):
    await seed_achievements(db_session)
    admin = await _account(db_session, "admin_dm", active=True, role="admin")
    alice = await _account(db_session, "alice", active=active)

    _sign_in(client, "admin_dm")
    resp = await client.post("/api/portal/requests", json={
        "tmdb_id": 12345, "media_type": "movie", "title": "Test Movie", "on_behalf_of": alice,
    })

    assert resp.status_code == 200, resp.text
    owner = await db_session.scalar(select(MediaRequest.user_id).where(MediaRequest.id == resp.json()["id"]))
    assert owner == alice
    _assert_paid(await _earned(db_session, alice), active)
    assert await _earned(db_session, admin) == (0, 0)


@ACTIVE
@pytest.mark.asyncio
async def test_items_added_to_a_shared_list_pay_only_an_active_owner(db_session, monkeypatch, active):
    monkeypatch.setattr(lists_svc, "_rl_bucket", {})
    await seed_achievements(db_session)
    alice = await _account(db_session, "alice", active=active)
    bob = await _account(db_session, "bob", active=True)
    shared = UserList(user_id=alice, name="Test List", privacy=PRIVACY_COLLABORATIVE)
    db_session.add(shared)
    await db_session.flush()
    db_session.add(UserListContributor(list_id=shared.id, user_id=bob))
    await db_session.commit()
    list_id = shared.id

    result = await lists_items.add_items(db_session, list_id, bob, [
        {"tmdb_id": n, "media_type": "movie", "title": f"Test Movie {n}"} for n in range(1, 11)
    ])

    assert result["added"] == 10
    _assert_paid(await _earned(db_session, alice), active)


@pytest.mark.parametrize(("source", "earns"), [("emby", True), ("local", False)])
@pytest.mark.asyncio
async def test_a_request_pays_its_author_only_if_linked_to_the_media_server(
    client, db_session, background_on_test_db, source, earns,
):
    await seed_achievements(db_session)
    admin = await _account(db_session, "admin_dm", active=True, role="admin", source=source)

    _sign_in(client, "admin_dm")
    resp = await client.post("/api/portal/requests", json={
        "tmdb_id": 12345, "media_type": "movie", "title": "Test Movie",
    })

    assert resp.status_code == 200, resp.text
    _assert_paid(await _earned(db_session, admin), earns)
