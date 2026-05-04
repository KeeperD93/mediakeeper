"""Backend behaviour when a chat message's author has been hard-deleted.

The FK becomes ``ON DELETE SET NULL`` from migration 040 onwards, so a
purge does not erase the message — instead ``user_id`` flips to NULL.
The serializer surfaces this as ``user_deleted=True`` so the frontend
can render an anonymous placeholder.

The actual DB-level cascade is verified by ``tests/test_migration_040_gdpr.py``
(schema inspection of the post-upgrade FK). The tests below exercise
the Python serializer in both states (live user / anonymised user).
"""
from datetime import datetime, timezone

import pytest

from models.portal.chat import ChatMessage
from services.portal.chat_presenters import serialize_message


@pytest.mark.asyncio
async def test_serialize_marks_user_deleted_when_user_id_is_null():
    msg = ChatMessage(
        id=1,
        room_id=1,
        user_id=None,
        content="hi",
        created_at=datetime.now(timezone.utc),
    )
    out = serialize_message(msg, user_name="ignored-once-deleted")
    assert out["user_id"] is None
    assert out["user_deleted"] is True
    assert out["user_name"] is None


@pytest.mark.asyncio
async def test_serialize_keeps_user_name_when_user_still_present():
    msg = ChatMessage(
        id=2,
        room_id=1,
        user_id=42,
        content="hi",
        created_at=datetime.now(timezone.utc),
    )
    out = serialize_message(msg, user_name="alice")
    assert out["user_id"] == 42
    assert out["user_deleted"] is False
    assert out["user_name"] == "alice"


@pytest.mark.asyncio
async def test_serialize_falls_back_to_id_marker_for_unknown_live_user():
    """Live user (user_id present) but no display_name resolved — the
    consumer renders the ``#<id>`` marker as before."""
    msg = ChatMessage(
        id=3,
        room_id=1,
        user_id=99,
        content="hi",
        created_at=datetime.now(timezone.utc),
    )
    out = serialize_message(msg, user_name=None)
    assert out["user_id"] == 99
    assert out["user_deleted"] is False
    assert out["user_name"] is None  # ChatPanel.vue renders ``#99`` from this
