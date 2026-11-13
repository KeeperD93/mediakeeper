"""``batch-status`` names the requester by their public name, never their sign-in name.

The "Requested by" tooltip of the portal media cards and media page reads
``requested_by``: it must show what the chat shows (chosen pseudo, generated
pseudo, admin label), to members and admins alike.
"""
import pytest

from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.user import User
from services.portal._pseudo_words import generate_pseudo

ROUTE = "/api/portal/requests/batch-status"


async def _user(
    db,
    login: str,
    *,
    display: str | None = None,
    must_set: bool = True,
    role: str = "viewer",
    with_profile: bool = True,
) -> User:
    user = User(
        username=login,
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if with_profile:
        db.add(UserProfile(
            user_id=user.id,
            display_name=display,
            display_name_must_set=must_set,
            role=role,
            account_active=True,
        ))
        await db.commit()
    return user


async def _request(db, user: User, tmdb_id: int) -> None:
    db.add(MediaRequest(
        user_id=user.id, tmdb_id=tmdb_id, media_type="movie",
        title="Test Movie", status="pending",
    ))
    await db.commit()


async def _requested_by(client, viewer: User, tmdb_id: int, locale: str = "fr") -> str:
    client.cookies.set(
        "rq_token", create_access_token({"sub": viewer.username, "scope": "portal"}),
    )
    resp = await client.post(
        ROUTE, json={"tmdb_ids": [tmdb_id]}, headers={"x-mk-locale": locale},
    )
    assert resp.status_code == 200
    return resp.json()["results"][str(tmdb_id)]["requested_by"]


@pytest.mark.asyncio
async def test_chosen_pseudo_is_shown(client, db_session):
    requester = await _user(db_session, "alice_login", display="Alice", must_set=False)
    viewer = await _user(db_session, "bob_login", display="Bob", must_set=False)
    await _request(db_session, requester, 12345)

    assert await _requested_by(client, viewer, 12345) == "Alice"


@pytest.mark.asyncio
async def test_unconfirmed_name_shows_the_generated_pseudo(client, db_session):
    # An imported account stores its media-server name until its owner confirms one.
    requester = await _user(db_session, "carol_emby", display="carol_emby", must_set=True)
    viewer = await _user(db_session, "bob_login", display="Bob", must_set=False)
    await _request(db_session, requester, 12346)

    shown = await _requested_by(client, viewer, 12346)
    assert shown == generate_pseudo(requester.id, "fr")
    assert shown != "carol_emby"


@pytest.mark.asyncio
@pytest.mark.parametrize(("locale", "label"), [("fr", "Administrateur"), ("en", "Administrator")])
async def test_admin_requester_shows_the_admin_label(client, db_session, locale, label):
    requester = await _user(
        db_session, "admin_login", display="admin_login", must_set=False, role="admin",
    )
    viewer = await _user(db_session, "bob_login", display="Bob", must_set=False)
    await _request(db_session, requester, 12347)

    assert await _requested_by(client, viewer, 12347, locale) == label


@pytest.mark.asyncio
async def test_requester_without_profile_shows_the_generated_pseudo(client, db_session):
    requester = await _user(db_session, "dave_login", with_profile=False)
    viewer = await _user(db_session, "bob_login", display="Bob", must_set=False)
    await _request(db_session, requester, 12348)

    shown = await _requested_by(client, viewer, 12348, "en")
    assert shown == generate_pseudo(requester.id, "en")
    assert shown != "dave_login"


@pytest.mark.asyncio
async def test_admin_viewer_gets_the_public_name_too(client, db_session):
    requester = await _user(db_session, "carol_emby", display="carol_emby", must_set=True)
    admin = await _user(
        db_session, "admin_login", display="Admin", must_set=False, role="admin",
    )
    await _request(db_session, requester, 12349)

    assert await _requested_by(client, admin, 12349) == generate_pseudo(requester.id, "fr")
