"""A fake media server and members for the sign-in tests that go through it."""
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import select

from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, hash_password
from models.portal.profile import UserProfile
from models.security import SecurityAttempt
from models.user import User

EMBY = {"source": "emby", "url": "http://emby.test", "api_key": "key"}
WRONG = "Wrong-Synthetic-1!"
ADMIN_PASSWORD = "TestPassword123!"
ACCEPTED = httpx.Response(200, json={"User": {"Id": "emby-id-a"}})


@contextmanager
def media_server(answer=None, *, raises=None, source=EMBY):
    http = AsyncMock()
    http.post = AsyncMock(return_value=answer, side_effect=raises)
    with patch("services.portal.emby_auth.get_active_media_source", new=AsyncMock(return_value=source)), \
         patch("services.portal.emby_auth.get_internal_client", return_value=http), \
         patch("api.auth._portal.get_unread_news", new=AsyncMock(return_value=[])):
        yield http


async def add_member(
    db_session, name="member-a", *, emby_id=None, active=True, account_active=True, switched_off=False, **profile,
) -> User:
    """``switched_off``: an admin or the expiry disabled it, which stamps this date.
    Inactive without it, the account has never been let in."""
    user = User(username=name, hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
                is_active=active, must_change_password=False)
    db_session.add(user)
    await db_session.commit()
    db_session.add(UserProfile(
        user_id=user.id, display_name=name, role="viewer", account_active=account_active, emby_user_id=emby_id,
        tokens_invalidated_at=datetime.now(timezone.utc) if switched_off else None, **profile,
    ))
    await db_session.commit()
    return user


async def failures(db_session) -> list[str]:
    return list((await db_session.execute(
        select(SecurityAttempt.scope).where(SecurityAttempt.success == 0)
    )).scalars().all())


async def sign_in(client, name="member-a", password=WRONG):
    return await client.post("/api/auth/portal-login", json={"username": name, "password": password})
