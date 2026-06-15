"""User-lists workflow: privacy, dedup, contributors, copy, admin moderation."""
import pytest
from sqlalchemy import select

from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.portal.social import (
    UserList, PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE, PRIVACY_PRIVATE,
)
from models.user import User


async def _bootstrap(db, username, role="viewer"):
    user = User(
        username=username,
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(UserProfile(
        user_id=user.id, display_name=username,
        role=role, account_active=True,
    ))
    await db.commit()
    return user


def _rq(client, user):
    client.cookies.set(
        "rq_token",
        create_access_token({"sub": user.username, "scope": "portal"}),
    )


@pytest.mark.asyncio
async def test_create_add_and_dedup(client, db_session):
    user = await _bootstrap(db_session, "alice")
    _rq(client, user)

    resp = await client.post("/api/portal/lists", json={
        "name": "Mon top",
        "privacy": "private",
        "content_type": "movies",
    })
    assert resp.status_code == 200
    list_id = resp.json()["id"]

    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [
            {"tmdb_id": 100, "media_type": "movie"},
            {"tmdb_id": 100, "media_type": "movie"},
            {"tmdb_id": 200, "media_type": "movie"},
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["added"] == 2
    assert body["duplicates"] == 1


@pytest.mark.asyncio
async def test_private_list_not_visible_to_other_user(client, db_session):
    owner = await _bootstrap(db_session, "owner")
    other = await _bootstrap(db_session, "stranger")

    _rq(client, owner)
    resp = await client.post("/api/portal/lists",
                             json={"name": "Secret", "privacy": "private"})
    list_id = resp.json()["id"]

    _rq(client, other)
    resp = await client.get(f"/api/portal/lists/{list_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_readonly_blocks_other_user_edits(client, db_session):
    owner = await _bootstrap(db_session, "pub_owner")
    other = await _bootstrap(db_session, "pub_other")

    _rq(client, owner)
    resp = await client.post("/api/portal/lists",
                             json={"name": "Public", "privacy": "public_readonly"})
    list_id = resp.json()["id"]

    _rq(client, other)
    # Non-owner can view
    assert (await client.get(f"/api/portal/lists/{list_id}")).status_code == 200
    # Non-owner cannot add
    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 1, "media_type": "movie"}],
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_collaborative_requires_contributor_optin(client, db_session):
    owner = await _bootstrap(db_session, "co_owner")
    friend = await _bootstrap(db_session, "co_friend")

    _rq(client, owner)
    resp = await client.post("/api/portal/lists",
                             json={"name": "Collab", "privacy": "collaborative"})
    list_id = resp.json()["id"]

    _rq(client, friend)
    # Not yet opted-in → cannot add
    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 1, "media_type": "movie"}],
    })
    assert resp.status_code == 403

    _rq(client, owner)
    resp = await client.post(f"/api/portal/lists/{list_id}/contributors",
                             json={"user_id": friend.id})
    assert resp.status_code == 200

    _rq(client, friend)
    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 777, "media_type": "movie"}],
    })
    assert resp.status_code == 200
    assert resp.json()["added"] == 1


@pytest.mark.asyncio
async def test_copy_public_list_notifies_owner(client, db_session):
    owner = await _bootstrap(db_session, "cp_owner")
    other = await _bootstrap(db_session, "cp_other")

    _rq(client, owner)
    resp = await client.post("/api/portal/lists",
                             json={"name": "Top", "privacy": "public_readonly"})
    list_id = resp.json()["id"]
    await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 1, "media_type": "movie"}],
    })

    _rq(client, other)
    resp = await client.post(f"/api/portal/lists/{list_id}/copy",
                             json={"new_name": "My copy"})
    assert resp.status_code == 200
    assert resp.json()["items_copied"] == 1

    from models.portal.event import MKNotification
    rows = (await db_session.execute(
        select(MKNotification).where(MKNotification.user_id == owner.id)
    )).scalars().all()
    assert any(n.type == "list_copied" for n in rows)


@pytest.mark.asyncio
async def test_delete_is_soft_and_admin_can_undelete(client, db_session):
    owner = await _bootstrap(db_session, "sd_owner")
    admin = await _bootstrap(db_session, "sd_admin", role="admin")

    _rq(client, owner)
    resp = await client.post("/api/portal/lists",
                             json={"name": "Rayon", "privacy": "private"})
    list_id = resp.json()["id"]

    resp = await client.delete(f"/api/portal/lists/{list_id}")
    assert resp.status_code == 200

    lst = await db_session.get(UserList, list_id)
    await db_session.refresh(lst)
    assert lst.is_deleted is True

    _rq(client, admin)
    resp = await client.post(f"/api/portal/admin/lists/{list_id}/undelete")
    assert resp.status_code == 200

    await db_session.refresh(lst)
    assert lst.is_deleted is False


@pytest.mark.asyncio
async def test_history_is_logged(client, db_session):
    user = await _bootstrap(db_session, "hist_owner")
    _rq(client, user)

    resp = await client.post("/api/portal/lists",
                             json={"name": "Audit", "privacy": "private"})
    list_id = resp.json()["id"]

    await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 42, "media_type": "movie"}],
    })

    resp = await client.get(f"/api/portal/lists/{list_id}/history")
    assert resp.status_code == 200
    actions = [entry["action"] for entry in resp.json()["items"]]
    assert "created" in actions
    assert "added" in actions


@pytest.mark.asyncio
async def test_export_json(client, db_session):
    user = await _bootstrap(db_session, "exp_owner")
    _rq(client, user)
    list_id = (await client.post("/api/portal/lists",
                                 json={"name": "Export"})).json()["id"]
    await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 7, "media_type": "movie"}],
    })

    resp = await client.get(f"/api/portal/lists/{list_id}/export?fmt=json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert "attachment" in resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_add_item_drops_javascript_scheme_poster_url(client, db_session):
    """A user-supplied ``poster_url`` carrying ``javascript:`` is rejected
    at persistence — the row stores ``NULL`` and the rendering layer
    falls back to the placeholder. Defence in depth even though
    ``<img src=javascript:...>`` does not execute on modern browsers."""
    user = await _bootstrap(db_session, "xss_owner")
    _rq(client, user)
    list_id = (await client.post("/api/portal/lists",
                                 json={"name": "XSS"})).json()["id"]

    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{
            "tmdb_id": 101, "media_type": "movie",
            "poster_url": "javascript:alert(1)",
        }],
    })
    assert resp.status_code == 200

    body = (await client.get(f"/api/portal/lists/{list_id}")).json()
    assert body["items"][0]["poster_url"] is None


@pytest.mark.asyncio
async def test_add_item_drops_data_uri_poster_url(client, db_session):
    user = await _bootstrap(db_session, "data_owner")
    _rq(client, user)
    list_id = (await client.post("/api/portal/lists",
                                 json={"name": "Data"})).json()["id"]

    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{
            "tmdb_id": 102, "media_type": "movie",
            "poster_url": "data:image/svg+xml,<svg/onload=alert(1)>",
        }],
    })
    assert resp.status_code == 200
    body = (await client.get(f"/api/portal/lists/{list_id}")).json()
    assert body["items"][0]["poster_url"] is None


@pytest.mark.asyncio
async def test_add_item_drops_off_whitelist_host(client, db_session):
    """``https://evil.example.com/poster.jpg`` is HTTPS but outside the
    poster CDN whitelist (``image.tmdb.org`` / ``i.imgur.com``) — the
    backend refuses to persist it."""
    user = await _bootstrap(db_session, "host_owner")
    _rq(client, user)
    list_id = (await client.post("/api/portal/lists",
                                 json={"name": "Host"})).json()["id"]

    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{
            "tmdb_id": 103, "media_type": "movie",
            "poster_url": "https://evil.example.com/poster.jpg",
        }],
    })
    assert resp.status_code == 200
    body = (await client.get(f"/api/portal/lists/{list_id}")).json()
    assert body["items"][0]["poster_url"] is None


@pytest.mark.asyncio
async def test_add_item_keeps_whitelisted_tmdb_poster(client, db_session):
    user = await _bootstrap(db_session, "ok_owner")
    _rq(client, user)
    list_id = (await client.post("/api/portal/lists",
                                 json={"name": "OK"})).json()["id"]

    poster = "https://image.tmdb.org/t/p/w500/abc.jpg"
    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{
            "tmdb_id": 104, "media_type": "movie",
            "poster_url": poster,
        }],
    })
    assert resp.status_code == 200
    body = (await client.get(f"/api/portal/lists/{list_id}")).json()
    assert body["items"][0]["poster_url"] == poster


@pytest.mark.asyncio
async def test_public_lists_cursor_pagination(client, db_session):
    owner = await _bootstrap(db_session, "pg_owner")
    db_session.add_all([
        UserList(user_id=owner.id, name=f"Public {i:02d}", privacy=PRIVACY_PUBLIC_READONLY)
        for i in range(5)
    ])
    await db_session.commit()
    _rq(client, owner)

    seen: list[int] = []
    cursor = None
    for _ in range(10):  # safety bound well above the 5 seeded lists
        url = "/api/portal/lists/public?limit=2" + (f"&cursor={cursor}" if cursor else "")
        resp = await client.get(url)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        seen.extend(it["id"] for it in body["items"])
        cursor = body.get("next_cursor")
        if not cursor:
            break
    assert len(seen) == 5 and len(set(seen)) == 5


@pytest.mark.asyncio
async def test_public_lists_rejects_forged_cursor(client, db_session):
    """A cursor with a malformed timestamp is ignored (served from the top),
    never a 500."""
    from core.pagination import encode_cursor

    owner = await _bootstrap(db_session, "pg_forged_owner")
    db_session.add(UserList(
        user_id=owner.id, name="Visible", privacy=PRIVACY_PUBLIC_READONLY,
    ))
    await db_session.commit()
    _rq(client, owner)

    forged = encode_cursor({"updated_at": "not-a-date", "id": 1})
    resp = await client.get(f"/api/portal/lists/public?limit=2&cursor={forged}")
    assert resp.status_code == 200
    assert any(it["name"] == "Visible" for it in resp.json()["items"])


@pytest.mark.asyncio
async def test_public_list_owner_alias_localized_to_viewer(client, db_session):
    # Owner with no chosen pseudo → rendered as the anonymous alias, which
    # must follow the viewer's Accept-Language (not a hardcoded French default).
    owner = User(
        username="silent-owner", hashed_password=hash_password("Irrelevant123!"),
        is_active=True, must_change_password=False,
    )
    db_session.add(owner)
    await db_session.commit()
    await db_session.refresh(owner)
    # ``display_name_must_set`` makes the serializer ignore the stored name
    # and fall back to the anonymous alias, regardless of the column value.
    db_session.add(UserProfile(
        user_id=owner.id, display_name="silent-owner", display_name_must_set=True,
        role="viewer", account_active=True,
    ))
    db_session.add(UserList(
        user_id=owner.id, name="Public", privacy=PRIVACY_PUBLIC_READONLY,
    ))
    await db_session.commit()
    _rq(client, owner)

    en = (await client.get(
        "/api/portal/lists/public", headers={"Accept-Language": "en"},
    )).json()
    row = next(r for r in en["items"] if r["owner_id"] == owner.id)
    assert row["owner_username"].startswith("User ")

    fr = (await client.get(
        "/api/portal/lists/public", headers={"Accept-Language": "fr"},
    )).json()
    row = next(r for r in fr["items"] if r["owner_id"] == owner.id)
    assert row["owner_username"].startswith("Utilisateur ")


@pytest.mark.asyncio
async def test_contributor_sees_alias_for_soft_deleted_owner(client, db_session):
    from datetime import datetime, timezone

    owner = await _bootstrap(db_session, "co-owner-del")
    friend = await _bootstrap(db_session, "co-friend")
    # Give the owner a chosen pseudo so a verbatim leak would be observable.
    owner_profile = (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == owner.id)
    )).scalar_one()
    owner_profile.display_name = "RealOwner"
    owner_profile.display_name_must_set = False
    db_session.add(owner_profile)
    await db_session.commit()

    _rq(client, owner)
    list_id = (await client.post(
        "/api/portal/lists", json={"name": "Collab", "privacy": "collaborative"},
    )).json()["id"]
    await client.post(f"/api/portal/lists/{list_id}/contributors", json={"user_id": friend.id})

    # Sanity: while the owner is active the contributor sees the real pseudo.
    _rq(client, friend)
    row = next(
        r for r in (await client.get("/api/portal/lists")).json()["items"]
        if r["id"] == list_id
    )
    assert row["owner_username"] == "RealOwner"

    # Soft-delete the owner → the contributor must see the anonymous alias.
    owner_profile.account_active = False
    owner_profile.deleted_at = datetime.now(timezone.utc)
    owner.is_active = False
    db_session.add_all([owner_profile, owner])
    await db_session.commit()

    row = next(
        r for r in (await client.get("/api/portal/lists")).json()["items"]
        if r["id"] == list_id
    )
    assert row["owner_username"] != "RealOwner"
    assert row["owner_username"].startswith("Utilisateur ")


@pytest.mark.asyncio
async def test_moderation_shows_soft_deleted_private_for_restore(client, db_session):
    owner = await _bootstrap(db_session, "priv-owner")
    admin = await _bootstrap(db_session, "priv-admin", role="admin")
    # An active private list stays out of moderation; a soft-deleted one shows
    # so the admin can restore it.
    db_session.add_all([
        UserList(user_id=owner.id, name="ActivePrivate", privacy=PRIVACY_PRIVATE),
        UserList(
            user_id=owner.id, name="DeletedPrivate",
            privacy=PRIVACY_PRIVATE, is_deleted=True,
        ),
    ])
    await db_session.commit()
    _rq(client, admin)

    body = (await client.get("/api/portal/admin/lists")).json()
    names = [r["name"] for r in body["items"]]
    assert "DeletedPrivate" in names
    assert "ActivePrivate" not in names


@pytest.mark.asyncio
async def test_public_lists_hide_soft_deleted_from_users(client, db_session):
    """The user-facing /public endpoint must never leak a soft-deleted list."""
    owner = await _bootstrap(db_session, "pd_owner")
    db_session.add(UserList(
        user_id=owner.id, name="Gone", privacy=PRIVACY_PUBLIC_READONLY, is_deleted=True,
    ))
    await db_session.commit()
    _rq(client, owner)

    body = (await client.get("/api/portal/lists/public")).json()
    assert all(it["name"] != "Gone" for it in body["items"])
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_moderation_lists_include_soft_deleted_for_admin(client, db_session):
    """Admin moderation sees soft-deleted lists so the undelete button works."""
    owner = await _bootstrap(db_session, "mod_owner")
    admin = await _bootstrap(db_session, "mod_admin", role="admin")
    db_session.add_all([
        UserList(user_id=owner.id, name="Live one", privacy=PRIVACY_PUBLIC_READONLY),
        UserList(user_id=owner.id, name="Deleted one",
                 privacy=PRIVACY_PUBLIC_READONLY, is_deleted=True),
    ])
    await db_session.commit()
    _rq(client, admin)

    body = (await client.get("/api/portal/admin/lists")).json()
    names = {it["name"] for it in body["items"]}
    assert {"Live one", "Deleted one"} <= names
    assert body["total"] == 2


@pytest.mark.asyncio
async def test_moderation_lists_cursor_pagination(client, db_session):
    owner = await _bootstrap(db_session, "modpg_owner")
    admin = await _bootstrap(db_session, "modpg_admin", role="admin")
    db_session.add_all([
        UserList(user_id=owner.id, name=f"Mod {i:02d}", privacy=PRIVACY_COLLABORATIVE)
        for i in range(5)
    ])
    await db_session.commit()
    _rq(client, admin)

    seen: list[int] = []
    cursor = None
    for _ in range(10):  # safety bound well above the 5 seeded lists
        url = "/api/portal/admin/lists?limit=2" + (f"&cursor={cursor}" if cursor else "")
        resp = await client.get(url)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        seen.extend(it["id"] for it in body["items"])
        cursor = body.get("next_cursor")
        if not cursor:
            break
    assert len(seen) == 5 and len(set(seen)) == 5


@pytest.mark.asyncio
async def test_moderation_lists_rejects_non_admin(client, db_session):
    """The moderation feed exposes deleted lists → must stay admin-only."""
    viewer = await _bootstrap(db_session, "mod_viewer")
    _rq(client, viewer)
    resp = await client.get("/api/portal/admin/lists")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mutation_schemas_reject_unknown_fields(client, db_session):
    """A payload carrying an unexpected field is rejected (422) rather than
    silently ignored — defence in depth against forged requests."""
    user = await _bootstrap(db_session, "forbid_owner")
    _rq(client, user)

    # Top-level schema (ListCreate)
    resp = await client.post("/api/portal/lists", json={
        "name": "Strict", "privacy": "private", "is_admin": True,
    })
    assert resp.status_code == 422

    list_id = (await client.post(
        "/api/portal/lists", json={"name": "Strict"},
    )).json()["id"]

    # Nested schema (ItemPayload inside ItemsAdd)
    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 1, "media_type": "movie", "rating": 9.5}],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_item_unproxies_image_cache_poster(client, db_session):
    """With the admin image cache on, a card hands the list the local
    proxy URL, not the raw TMDB URL. The list must recover the canonical
    TMDB URL behind it instead of dropping the poster — the proxy path is
    not on the poster host whitelist, so a naive whitelist would NULL it."""
    from services.portal.image_cache import proxied_url

    user = await _bootstrap(db_session, "proxy_owner")
    _rq(client, user)
    list_id = (await client.post(
        "/api/portal/lists", json={"name": "Proxy"},
    )).json()["id"]

    tmdb = "https://image.tmdb.org/t/p/w300/abc.jpg"
    proxied = proxied_url(tmdb)
    assert proxied != tmdb  # sanity: the URL really got proxied

    resp = await client.post(f"/api/portal/lists/{list_id}/items", json={
        "items": [{"tmdb_id": 555, "media_type": "movie", "poster_url": proxied}],
    })
    assert resp.status_code == 200

    body = (await client.get(f"/api/portal/lists/{list_id}")).json()
    assert body["items"][0]["poster_url"] == tmdb


@pytest.mark.asyncio
async def test_admin_mute_rejects_unknown_fields(client, db_session):
    owner = await _bootstrap(db_session, "fb_mute_owner")
    admin = await _bootstrap(db_session, "fb_mute_admin", role="admin")
    _rq(client, owner)
    list_id = (await client.post(
        "/api/portal/lists", json={"name": "Collab", "privacy": "collaborative"},
    )).json()["id"]

    _rq(client, admin)
    resp = await client.post(f"/api/portal/admin/lists/{list_id}/mute-owner", json={
        "muted": True, "forever": True,
    })
    assert resp.status_code == 422
