"""Privacy boundary on the list contributors panel.

When the ``GET /api/portal/lists/{list_id}`` route returns the
collaborative-list contributors panel, the per-row ``username`` field
must NEVER expose the raw Emby login of a contributor who has not
picked a portal pseudo yet — the localized anonymous alias is
surfaced instead.
"""
from __future__ import annotations

import pytest

from models.portal.social import (
    PRIVACY_COLLABORATIVE,
    UserList,
    UserListContributor,
)
from services.portal._pseudo_words import generate_pseudo
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


async def _make_collab_list_with_contributor(
    db_session, *, owner_username, contributor_username, contributor_must_set,
):
    owner, _ = await make_portal_user(db_session, username=owner_username)
    contributor, _ = await make_portal_user(
        db_session,
        username=contributor_username,
        must_set=contributor_must_set,
    )
    lst = UserList(
        user_id=owner.id,
        name="Collab list",
        privacy=PRIVACY_COLLABORATIVE,
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)
    db_session.add(UserListContributor(list_id=lst.id, user_id=contributor.id))
    await db_session.commit()
    return owner, contributor, lst


@pytest.mark.asyncio
async def test_contributor_without_pseudo_renders_anonymous_alias(client, db_session):
    """A contributor that has not picked a pseudo renders as the
    localized alias on the panel — the raw Emby login MUST NOT leak."""
    owner, contributor, lst = await _make_collab_list_with_contributor(
        db_session,
        owner_username="lc-owner-1",
        contributor_username="my_emby_login",  # value that MUST NOT leak
        contributor_must_set=True,
    )

    client.cookies.set(PORTAL_COOKIE, portal_token(owner.username))
    resp = await client.get(f"/api/portal/lists/{lst.id}")
    assert resp.status_code == 200
    contributors = resp.json().get("contributors") or []
    row = next((c for c in contributors if c["user_id"] == contributor.id), None)
    assert row is not None
    expected = generate_pseudo(contributor.id, "fr")
    assert row["username"] == expected
    assert row["username"] != "my_emby_login"


@pytest.mark.asyncio
async def test_contributor_with_pseudo_returns_real_value(client, db_session):
    """Once the contributor has picked a pseudo, the panel surfaces
    that value verbatim — the alias path is only the fallback."""
    owner, contributor, lst = await _make_collab_list_with_contributor(
        db_session,
        owner_username="lc-owner-2",
        contributor_username="emby_login_2",
        contributor_must_set=False,
    )

    client.cookies.set(PORTAL_COOKIE, portal_token(owner.username))
    resp = await client.get(f"/api/portal/lists/{lst.id}")
    assert resp.status_code == 200
    contributors = resp.json().get("contributors") or []
    row = next((c for c in contributors if c["user_id"] == contributor.id), None)
    assert row is not None
    # ``make_portal_user`` defaults ``display_name`` to ``username`` —
    # the resolver therefore returns the chosen pseudo verbatim.
    assert row["username"] == "emby_login_2"


@pytest.mark.asyncio
async def test_owner_without_pseudo_renders_anonymous_alias(client, db_session):
    """The same privacy boundary applies to ``owner_username`` on the
    list detail payload — a viewer that opens a list owned by an
    account without a pseudo must see the localized alias, never the
    raw Emby login."""
    owner, _ = await make_portal_user(
        db_session,
        username="lo_emby_login",  # value that MUST NOT leak
        must_set=True,
    )
    viewer, _ = await make_portal_user(db_session, username="lo-viewer-1")
    lst = UserList(
        user_id=owner.id,
        name="Public list",
        privacy=PRIVACY_COLLABORATIVE,
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))
    resp = await client.get(f"/api/portal/lists/{lst.id}")
    assert resp.status_code == 200
    body = resp.json()
    expected = generate_pseudo(owner.id, "fr")
    assert body["owner_username"] == expected
    assert body["owner_username"] != "lo_emby_login"


@pytest.mark.asyncio
async def test_owner_with_pseudo_returns_real_value(client, db_session):
    """Once the owner has picked a pseudo, the list detail surfaces
    that value verbatim under ``owner_username``."""
    owner, _ = await make_portal_user(
        db_session,
        username="lo_emby_login_2",
        must_set=False,
    )
    viewer, _ = await make_portal_user(db_session, username="lo-viewer-2")
    lst = UserList(
        user_id=owner.id,
        name="Public list 2",
        privacy=PRIVACY_COLLABORATIVE,
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))
    resp = await client.get(f"/api/portal/lists/{lst.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["owner_username"] == "lo_emby_login_2"


@pytest.mark.asyncio
async def test_contributor_alias_localizes_to_english(client, db_session):
    """``Accept-Language`` drives the pseudo language: ``Renard-Bleu-42``
    in FR, ``Blue-Fox-42`` in EN."""
    owner, contributor, lst = await _make_collab_list_with_contributor(
        db_session,
        owner_username="lc-owner-3",
        contributor_username="emby_login_3",
        contributor_must_set=True,
    )

    client.cookies.set(PORTAL_COOKIE, portal_token(owner.username))
    resp = await client.get(
        f"/api/portal/lists/{lst.id}",
        headers={"accept-language": "en-US,en;q=0.9,fr;q=0.8"},
    )
    assert resp.status_code == 200
    contributors = resp.json().get("contributors") or []
    row = next((c for c in contributors if c["user_id"] == contributor.id), None)
    assert row is not None
    assert row["username"] == generate_pseudo(contributor.id, "en")
