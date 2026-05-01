"""
MediaKeeper Events facade — public API for the multi-film event system.

Backs the private/public events flow specified in ROADMAP §16: multi-film
marathons, invitations with retry caps, public events broadcast to all
users, conflict detection, room entry, and seat allocation. Notifications
are dispatched via services/portal/notifications.

Implementation is split across four modules to keep each file under 300 lines:

  - mk_events_utils.py    — constants, user label resolver, event serializer,
                             scheduling conflict check.
  - mk_events_crud.py     — create/update/cancel/list/get_one.
  - mk_events_members.py  — invite, accept/decline, remove, enter_room.
  - mk_events_chat.py     — list_messages, post_message.

Consumers import from this file, not the split modules, so the public API
stays stable.
"""
from services.portal.mk_events_utils import (
    MAX_INVITE_RETRIES,
    MAX_PARTICIPANTS,
    ROOM_OPEN_BEFORE_MIN,
)
from services.portal.mk_events_crud import (
    create_event,
    update_event,
    cancel_event,
    list_for_user,
    list_upcoming_admin,
    get_one,
)
from services.portal.mk_events_members import (
    invite_user,
    respond,
    remove_member,
    enter_room,
)
from services.portal.mk_events_chat import (
    list_messages,
    post_message,
)

__all__ = [
    # Constants
    "MAX_INVITE_RETRIES", "MAX_PARTICIPANTS", "ROOM_OPEN_BEFORE_MIN",
    # CRUD
    "create_event", "update_event", "cancel_event", "list_for_user",
    "list_upcoming_admin", "get_one",
    # Membership
    "invite_user", "respond", "remove_member", "enter_room",
    # Chat
    "list_messages", "post_message",
]
