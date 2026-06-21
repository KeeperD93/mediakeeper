"""Event-room chat messages are HTML-sanitised at storage (#407)."""
from datetime import datetime, timezone

import pytest

from models.portal.event import MKEvent, MKEventInvitation
from services.portal.mk_events_chat import post_message
from tests._portal_profile_helpers import make_portal_user


@pytest.mark.asyncio
async def test_event_chat_strips_html(db_session):
    """Event-room messages are sanitised at storage like the global chat."""
    user, _ = await make_portal_user(db_session, username="evt_chatter")
    event = MKEvent(
        creator_user_id=user.id, title="Movie night", kind="private",
        tmdb_ids=[1], scheduled_at=datetime.now(timezone.utc),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    db_session.add(
        MKEventInvitation(event_id=event.id, user_id=user.id, status="accepted")
    )
    await db_session.commit()

    res = await post_message(
        db_session, event.id, user.id, "<b>hi</b><script>x</script>",
    )
    assert "<" not in res["content"]
    assert "hi" in res["content"]
