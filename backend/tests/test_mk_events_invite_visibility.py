"""Event invitations must honour profile visibility.

A private profile or the admin account can never be added as a guest — not
via the picker, the direct invite endpoint, nor a crafted create-event
``invitees`` payload. These tests pin the server-side enforcement so the
"private profile = not invitable" promise cannot silently regress.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models.portal.event import EventStatus, MKEvent, MKEventInvitation
from services.portal.mk_events_crud import create_event
from services.portal.mk_events_members import invite_user
from services.portal.mk_events_utils import MAX_PARTICIPANTS, is_invitable
from tests._portal_profile_helpers import make_portal_user


async def _make_event(db_session, creator_id: int) -> MKEvent:
    event = MKEvent(
        creator_user_id=creator_id,
        title="Movie Night",
        kind="private",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "Solo"}],
        scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        status=EventStatus.SCHEDULED.value,
        max_participants=MAX_PARTICIPANTS,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest.mark.asyncio
async def test_is_invitable_matches_picker_visibility(db_session):
    pub, _ = await make_portal_user(db_session, username="inv-pub", role="viewer", is_public=True)
    priv, _ = await make_portal_user(db_session, username="inv-priv", role="viewer", is_public=False)
    adm, _ = await make_portal_user(db_session, username="inv-adm", role="admin", is_public=True)

    assert await is_invitable(db_session, pub.id) is True
    assert await is_invitable(db_session, priv.id) is False   # private
    assert await is_invitable(db_session, adm.id) is False     # admin
    assert await is_invitable(db_session, 999999) is False     # no such profile


@pytest.mark.asyncio
async def test_invite_user_refuses_private_and_admin(db_session):
    creator, _ = await make_portal_user(db_session, username="inv-creator", role="viewer", is_public=True)
    pub, _ = await make_portal_user(db_session, username="inv-guest-pub", role="viewer", is_public=True)
    priv, _ = await make_portal_user(db_session, username="inv-guest-priv", role="viewer", is_public=False)
    adm, _ = await make_portal_user(db_session, username="inv-guest-adm", role="admin", is_public=True)
    event = await _make_event(db_session, creator.id)

    assert await invite_user(db_session, event.id, creator.id, priv.id) == {"error": "not_invitable"}
    assert await invite_user(db_session, event.id, creator.id, adm.id) == {"error": "not_invitable"}
    assert (await invite_user(db_session, event.id, creator.id, pub.id)).get("ok") is True


@pytest.mark.asyncio
async def test_create_event_drops_non_invitable_invitees(db_session):
    creator, _ = await make_portal_user(db_session, username="ce-creator", role="viewer", is_public=True)
    pub, _ = await make_portal_user(db_session, username="ce-pub", role="viewer", is_public=True)
    priv, _ = await make_portal_user(db_session, username="ce-priv", role="viewer", is_public=False)

    result = await create_event(
        db_session, creator.id,
        title="Soiree", kind="private",
        tmdb_ids=[{"tmdb_id": 1, "media_type": "movie", "title": "Solo"}],
        scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        comment=None, invitees=[pub.id, priv.id], max_participants=10,
    )
    assert "error" not in result, result

    event = (await db_session.execute(
        select(MKEvent).where(MKEvent.creator_user_id == creator.id)
    )).scalar_one()
    invited = set((await db_session.execute(
        select(MKEventInvitation.user_id).where(MKEventInvitation.event_id == event.id)
    )).scalars().all())
    assert pub.id in invited
    assert priv.id not in invited   # private invitee dropped at creation
