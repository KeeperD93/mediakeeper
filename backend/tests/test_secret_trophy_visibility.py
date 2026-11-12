"""Unearned secret trophies show their name and icon, never how they are earned.

Member payloads (own trophies, another player's trophies, the title
catalogue) hide the description and the progress of a secret until it is
unlocked, whatever its progress; the admin drawer keeps the full picture.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.security import create_access_token
from models.portal.achievement import UserAchievement
from services.portal.achievement_defs import ACHIEVEMENT_DEFS
from services.portal.achievements import seed_achievements
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

DEFS = {d["id"]: d for d in ACHIEVEMENT_DEFS}
SECRET_ID = "secret_night_owl"  # threshold 50
TITLED_SECRET_ID = "secret_insomnia"  # grants a title
UNLOCKED_TITLED_SECRET_ID = "secret_christmas"  # grants a title
STANDARD_ID = "movie_buff_1"  # threshold 10
HIDDEN = {
    "description_key": None,
    "progress": None,
    "threshold": None,
    "secret_theme": None,
    "seasonal_years": [],
}


async def _set_progress(db, user_id: int, ach_id: str, progress: int, *, unlocked: bool = False):
    db.add(UserAchievement(
        user_id=user_id,
        achievement_id=ach_id,
        progress=progress,
        unlocked=unlocked,
        unlocked_at=datetime.now(UTC) if unlocked else None,
    ))
    await db.commit()


async def _alice(client, db):
    await seed_achievements(db)
    user, profile = await make_portal_user(db, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    return user, profile


async def _my_item(client, ach_id: str) -> dict:
    r = await client.get("/api/portal/achievements/me")
    assert r.status_code == 200, r.text
    return next(i for i in r.json()["items"] if i["id"] == ach_id)


def _assert_hidden(item: dict, ach_id: str) -> None:
    assert item["status"] == "secret"
    assert item["name_key"] == DEFS[ach_id]["name_key"]
    assert item["icon"] == DEFS[ach_id]["icon"]
    assert {k: item[k] for k in HIDDEN} == HIDDEN


@pytest.mark.asyncio
async def test_unearned_secret_without_progress_shows_name_and_icon_only(client, db_session):
    await _alice(client, db_session)

    _assert_hidden(await _my_item(client, SECRET_ID), SECRET_ID)


@pytest.mark.asyncio
async def test_unearned_secret_with_progress_stays_secret(client, db_session):
    user, _ = await _alice(client, db_session)
    await _set_progress(db_session, user.id, SECRET_ID, 30)

    _assert_hidden(await _my_item(client, SECRET_ID), SECRET_ID)


@pytest.mark.asyncio
async def test_next_achievement_skips_unearned_secrets(client, db_session):
    user, _ = await _alice(client, db_session)
    await _set_progress(db_session, user.id, SECRET_ID, 30)  # 60 % of the way
    await _set_progress(db_session, user.id, STANDARD_ID, 1)  # 10 % of the way

    r = await client.get("/api/portal/achievements/me")

    assert r.json()["next_achievement"]["id"] == STANDARD_ID


@pytest.mark.asyncio
async def test_unlocked_secret_shows_everything(client, db_session):
    user, _ = await _alice(client, db_session)
    await _set_progress(db_session, user.id, SECRET_ID, 50, unlocked=True)

    item = await _my_item(client, SECRET_ID)

    assert item["status"] == "unlocked"
    assert item["description_key"] == DEFS[SECRET_ID]["description_key"]
    assert item["progress"] == 50
    assert item["threshold"] == DEFS[SECRET_ID]["threshold"]
    assert item["secret_theme"] == "night"


@pytest.mark.asyncio
async def test_other_player_trophies_never_reveal_an_unearned_secret(client, db_session):
    await _alice(client, db_session)
    bob, _ = await make_portal_user(db_session, username="bob")
    await _set_progress(db_session, bob.id, STANDARD_ID, 10, unlocked=True)
    await _set_progress(db_session, bob.id, SECRET_ID, 30)

    r = await client.get(f"/api/portal/achievements/user/{bob.id}")

    assert r.status_code == 200, r.text
    body = r.json()
    assert [i["id"] for i in body["items"]] == [STANDARD_ID]
    assert body["next_achievement"] is None
    assert DEFS[SECRET_ID]["description_key"] not in r.text


@pytest.mark.asyncio
async def test_title_catalogue_hides_how_to_earn_an_unearned_secret(client, db_session):
    user, _ = await _alice(client, db_session)
    await _set_progress(db_session, user.id, UNLOCKED_TITLED_SECRET_ID, 1, unlocked=True)

    r = await client.get("/api/portal/profiles/me/titles")

    assert r.status_code == 200, r.text
    by_id = {e["achievement_id"]: e for e in r.json()["catalogue"]}
    assert by_id[TITLED_SECRET_ID]["achievement_description_key"] is None
    assert by_id[TITLED_SECRET_ID]["achievement_name_key"] == DEFS[TITLED_SECRET_ID]["name_key"]
    assert (
        by_id[UNLOCKED_TITLED_SECRET_ID]["achievement_description_key"]
        == DEFS[UNLOCKED_TITLED_SECRET_ID]["description_key"]
    )


@pytest.mark.asyncio
async def test_admin_drawer_keeps_the_progress_of_an_unearned_secret(client, db_session, admin_user):
    await seed_achievements(db_session)
    bob, bob_profile = await make_portal_user(db_session, username="bob")
    await _set_progress(db_session, bob.id, SECRET_ID, 30)
    client.cookies.set(
        "mk_token", create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )

    r = await client.get(f"/api/portal/admin/users/{bob_profile.id}/trophies")

    assert r.status_code == 200, r.text
    item = next(i for i in r.json()["in_progress"] if i["id"] == SECRET_ID)
    assert (item["progress"], item["threshold"]) == (30, DEFS[SECRET_ID]["threshold"])
