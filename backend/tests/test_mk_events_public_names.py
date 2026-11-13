"""Events name people by their public name, never their sign-in name.

Event cards, guest lists, cinema seats and the event notifications show what
the chat shows: the chosen pseudo, the generated one while it is not
confirmed, the admin label for an admin.
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from core.i18n import DEFAULT_LOCALE
from core.security import hash_password
from models.portal.event import EventStatus, MKEvent, MKEventInvitation, MKNotification
from models.user import User
from services.portal import mk_events_crud
from services.portal._pseudo_words import generate_pseudo
from services.portal.mk_events_crud import create_event, list_for_user
from services.portal.mk_events_members import respond
from services.portal.mk_events_utils import (
    MAX_PARTICIPANTS,
    _serialize_event,
    _user_label,
)
from services.settings import set_setting
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


async def _event(db, creator_id: int, guest_ids: list[int]) -> MKEvent:
    event = MKEvent(
        creator_user_id=creator_id,
        title="Movie Night",
        kind="private",
        tmdb_ids=[{"tmdb_id": 12345, "media_type": "movie", "title": "Test Movie"}],
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        status=EventStatus.SCHEDULED.value,
        max_participants=MAX_PARTICIPANTS,
    )
    db.add(event)
    await db.flush()
    for uid in guest_ids:
        db.add(MKEventInvitation(event_id=event.id, user_id=uid, status="pending", invite_count=1))
    await db.commit()
    await db.refresh(event)
    return event


def _guest_name(serialized: dict, user_id: int) -> str:
    return next(i["username"] for i in serialized["invitations"] if i["user_id"] == user_id)


@pytest.mark.asyncio
async def test_guests_show_their_public_name(db_session):
    creator, _ = await make_portal_user(db_session, username="alice_login", display_name="Alice")
    chosen, _ = await make_portal_user(db_session, username="bob_login", display_name="Bob")
    # An imported account stores its media-server name until its owner confirms one.
    silent, _ = await make_portal_user(db_session, username="carol_emby", must_set=True)
    event = await _event(db_session, creator.id, [chosen.id, silent.id])

    out = await _serialize_event(db_session, event, "en")

    assert _guest_name(out, chosen.id) == "Bob"
    assert _guest_name(out, silent.id) == generate_pseudo(silent.id, "en")
    assert "carol_emby" not in str(out)
    assert out["creator_label"] == "Alice"


@pytest.mark.asyncio
@pytest.mark.parametrize(("lang", "label"), [("fr", "Administrateur"), ("en", "Administrator")])
async def test_admin_creator_shows_the_admin_label(db_session, lang, label):
    admin, _ = await make_portal_user(db_session, username="admin_login", role="admin")
    event = await _event(db_session, admin.id, [])

    assert (await _serialize_event(db_session, event, lang))["creator_label"] == label


@pytest.mark.asyncio
async def test_serialized_names_default_to_the_portal_language(db_session):
    creator, _ = await make_portal_user(db_session, username="dave_emby", must_set=True)
    event = await _event(db_session, creator.id, [])
    await set_setting(db_session, "portal.default_language", "en")

    assert (await _serialize_event(db_session, event))["creator_label"] == (
        generate_pseudo(creator.id, "en")
    )


@pytest.mark.asyncio
async def test_account_without_profile_gets_the_generated_pseudo(db_session):
    user = User(
        username="erin_login", hashed_password=hash_password("Irrelevant123!"),
        is_active=True, must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert await _user_label(db_session, user.id) == generate_pseudo(user.id, DEFAULT_LOCALE)
    assert await _user_label(db_session, None) is None


@pytest.mark.asyncio
async def test_invitation_and_reply_notifications_carry_the_public_name(db_session):
    creator, _ = await make_portal_user(db_session, username="frank_emby", must_set=True)
    guest, _ = await make_portal_user(db_session, username="gina_emby", must_set=True)

    created = await create_event(
        db_session, creator.id,
        title="Movie Night", kind="private",
        tmdb_ids=[{"tmdb_id": 12345, "media_type": "movie", "title": "Test Movie"}],
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        comment=None, invitees=[guest.id], max_participants=10,
    )
    assert "error" not in created, created
    assert (await respond(db_session, created["id"], guest.id, "accept")).get("ok") is True

    payloads = {
        n.user_id: n.payload
        for n in (await db_session.execute(select(MKNotification))).scalars().all()
    }
    assert payloads[guest.id]["from"] == generate_pseudo(creator.id, DEFAULT_LOCALE)
    assert payloads[creator.id]["from"] == generate_pseudo(guest.id, DEFAULT_LOCALE)
    assert "frank_emby" not in str(payloads) and "gina_emby" not in str(payloads)


@pytest.mark.asyncio
async def test_event_route_follows_the_viewer_language(client, db_session):
    creator, _ = await make_portal_user(db_session, username="hana_emby", must_set=True)
    guest, _ = await make_portal_user(db_session, username="ivan_emby", must_set=True)
    event = await _event(db_session, creator.id, [guest.id])

    client.cookies.set(PORTAL_COOKIE, portal_token(guest.username))
    resp = await client.get(f"/api/portal/events/rooms/{event.id}", headers={"x-mk-locale": "en"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["creator_label"] == generate_pseudo(creator.id, "en")
    assert _guest_name(body, guest.id) == generate_pseudo(guest.id, "en")


@pytest.mark.asyncio
async def test_admin_upcoming_widget_follows_the_reader_language(client, db_session):
    creator, _ = await make_portal_user(db_session, username="jane_emby", must_set=True)
    admin, _ = await make_portal_user(db_session, username="admin_login", role="admin")
    await _event(db_session, creator.id, [])

    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    resp = await client.get("/api/portal/admin/events/upcoming", headers={"x-mk-locale": "en"})

    assert resp.status_code == 200
    assert resp.json()["items"][0]["creator_label"] == generate_pseudo(creator.id, "en")


@pytest.mark.asyncio
async def test_event_list_reads_the_portal_language_once(db_session, monkeypatch):
    creator, _ = await make_portal_user(db_session, username="kim_emby", must_set=True)
    guest, _ = await make_portal_user(db_session, username="liam_emby", must_set=True)
    for _ in range(3):
        await _event(db_session, creator.id, [guest.id])
    calls = []

    async def _counting_default(db, default=None):  # noqa: ARG001
        calls.append(1)
        return "fr"

    monkeypatch.setattr(mk_events_crud, "get_portal_default_language", _counting_default)

    assert len(await list_for_user(db_session, guest.id)) == 3
    assert len(calls) == 1
