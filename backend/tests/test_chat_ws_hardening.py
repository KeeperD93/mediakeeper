"""Chat WebSocket hardening (#406): a per-connection message throttle (the
socket path bypasses the HTTP limiter) and a mid-session permission /
revocation recheck so a kicked user stops within seconds instead of only at
the next prune_revoked_ws_sessions sweep.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

import pytest

from api.portal.chat import (
    WS_MSG_LIMIT,
    WS_MSG_WINDOW_SEC,
    _over_rate_limit,
    _ws_still_authorized,
)
from models.portal.profile import UserProfile


# --- Sliding-window throttle (pure) ---

def test_over_rate_limit_allows_up_to_limit_then_drops():
    times: deque = deque()
    base = 1000.0
    for i in range(WS_MSG_LIMIT):
        assert _over_rate_limit(times, base + i * 0.1) is False
    # one more inside the window is dropped
    assert _over_rate_limit(times, base + WS_MSG_LIMIT * 0.1) is True


def test_over_rate_limit_window_slides():
    times: deque = deque()
    base = 1000.0
    for i in range(WS_MSG_LIMIT):
        _over_rate_limit(times, base + i * 0.1)
    # well past the window: every stamp expired, so a new message passes
    assert _over_rate_limit(times, base + WS_MSG_WINDOW_SEC + 1) is False


# --- Mid-session permission / revocation recheck ---

def _profile(user_id: int, **overrides) -> UserProfile:
    fields = dict(
        user_id=user_id, display_name="Chatter", role="viewer",
        account_active=True, can_chat=True, chat_enabled=True,
    )
    fields.update(overrides)
    return UserProfile(**fields)


@pytest.mark.asyncio
async def test_still_authorized_true_for_active_chatter(db_session, admin_user):
    db_session.add(_profile(admin_user.id))
    await db_session.commit()
    ok = await _ws_still_authorized(db_session, admin_user.id, datetime.now(timezone.utc))
    assert ok is True


@pytest.mark.asyncio
async def test_still_authorized_false_when_no_profile(db_session, admin_user):
    ok = await _ws_still_authorized(db_session, admin_user.id, datetime.now(timezone.utc))
    assert ok is False


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["account_active", "can_chat", "chat_enabled"])
async def test_still_authorized_false_when_flag_revoked(db_session, admin_user, flag):
    db_session.add(_profile(admin_user.id, **{flag: False}))
    await db_session.commit()
    ok = await _ws_still_authorized(db_session, admin_user.id, datetime.now(timezone.utc))
    assert ok is False


@pytest.mark.asyncio
async def test_still_authorized_honours_token_revocation_pivot(db_session, admin_user):
    pivot = datetime.now(timezone.utc)
    db_session.add(_profile(admin_user.id, tokens_invalidated_at=pivot))
    await db_session.commit()
    # token issued before the pivot → revoked
    stale = await _ws_still_authorized(db_session, admin_user.id, pivot - timedelta(minutes=5))
    assert stale is False
    # token issued after the pivot → still valid
    fresh = await _ws_still_authorized(db_session, admin_user.id, pivot + timedelta(minutes=5))
    assert fresh is True
