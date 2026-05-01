import json
from pathlib import PurePosixPath
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.portal.ticket import Ticket, TicketReply
from models.notification_log import NotificationLog
from models.user import User
from services.notification_engine.added_media import _send_item
from services.notification_engine.system import send_system_notification
from services.settings import set_notification_channel


async def _create_portal_user(db_session, username: str, *, role: str = "viewer"):
    user = User(
        username=username,
        hashed_password=hash_password("TestPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username.title(),
        role=role,
        account_active=True,
        chat_enabled=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


class _FakePath:
    existing_paths: set[str] = set()
    created_paths: set[str] = set()

    def __init__(self, raw):
        self._path = PurePosixPath(str(raw))

    def resolve(self, strict=False):
        return _FakePath(self._path)

    @property
    def parent(self):
        return _FakePath(self._path.parent)

    @property
    def parts(self):
        return self._path.parts

    def exists(self):
        return str(self._path) in self.existing_paths or str(self._path) in self.created_paths

    def mkdir(self, parents=False, exist_ok=False):
        self.created_paths.add(str(self._path))

    def is_dir(self):
        return self.exists()

    def __truediv__(self, other):
        return _FakePath(self._path / str(other))

    def __str__(self):
        return str(self._path)

    def __repr__(self):
        return f"_FakePath({self._path!s})"

    def __eq__(self, other):
        return isinstance(other, _FakePath) and self._path == other._path

    def __hash__(self):
        return hash(self._path)


@pytest.mark.asyncio
async def test_create_folders_batch_rejects_parent_escape(monkeypatch):
    from services.media_manager import move as move_service

    _FakePath.existing_paths = {"/media-root", "/media-root/Series"}
    _FakePath.created_paths = set()

    monkeypatch.setattr(move_service, "_validate_path", lambda path: None)
    monkeypatch.setattr(move_service, "Path", _FakePath)

    payload = await move_service.create_folders_batch([
        {"parent_path": "/media-root/Series", "folder_name": "../outside"},
    ])

    assert payload[0]["error"] in {"name_not_allowed", "path_not_allowed"}
    assert "/media-root/outside" not in _FakePath.created_paths


@pytest.mark.asyncio
async def test_create_folders_batch_still_creates_valid_child(monkeypatch):
    from services.media_manager import move as move_service

    _FakePath.existing_paths = {"/media-root", "/media-root/Series"}
    _FakePath.created_paths = set()

    monkeypatch.setattr(move_service, "_validate_path", lambda path: None)
    monkeypatch.setattr(move_service, "Path", _FakePath)

    payload = await move_service.create_folders_batch([
        {"parent_path": "/media-root/Series", "folder_name": "Season 01"},
    ])

    assert payload[0]["success"] is True
    assert "/media-root/Series/Season 01" in _FakePath.created_paths


@pytest.mark.asyncio
async def test_ticket_reply_forbidden_for_other_non_admin(client, db_session):
    owner, _ = await _create_portal_user(db_session, "owner")
    other, _ = await _create_portal_user(db_session, "other")
    ticket = Ticket(
        user_id=owner.id,
        media_title="Demo",
        media_type="movie",
        issue_type="other",
        description="broken",
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)

    client.cookies.set("rq_token", create_access_token({"sub": other.username, "scope": "portal"}))
    resp = await client.post(f"/api/portal/tickets/{ticket.id}/reply", json={"content": "hello"})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "forbidden"


@pytest.mark.asyncio
async def test_ticket_reply_owner_and_admin_still_allowed(client, db_session):
    owner, _ = await _create_portal_user(db_session, "owner")
    admin, _ = await _create_portal_user(db_session, "admin_dm", role="admin")
    ticket = Ticket(
        user_id=owner.id,
        media_title="Demo",
        media_type="movie",
        issue_type="other",
        description="broken",
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)

    client.cookies.set("rq_token", create_access_token({"sub": owner.username, "scope": "portal"}))
    owner_resp = await client.post(f"/api/portal/tickets/{ticket.id}/reply", json={"content": "owner reply"})
    assert owner_resp.status_code == 200

    with patch("services.portal.notifications.create", new=AsyncMock(return_value={"success": True})):
        client.cookies.set("rq_token", create_access_token({"sub": admin.username, "scope": "portal"}))
        admin_resp = await client.post(f"/api/portal/tickets/{ticket.id}/reply", json={"content": "admin reply"})

    assert admin_resp.status_code == 200

    replies = (await db_session.execute(select(TicketReply).order_by(TicketReply.id.asc()))).scalars().all()
    assert [reply.content for reply in replies] == ["owner reply", "admin reply"]


@pytest.mark.asyncio
async def test_added_media_logs_failed_when_discord_rejects(db_session):
    with patch(
        "services.notification_engine.added_media.build_discord_payload",
        new=AsyncMock(return_value={"content": "demo"}),
    ), patch(
        "services.notification_engine.added_media.send_discord_webhook",
        new=AsyncMock(return_value=False),
    ):
        await _send_item(
            db_session,
            {"Type": "Movie", "Name": "Demo Movie"},
            [{"enabled": True, "events": {"added": True}, "name": "Main", "url": "https://discord.com/api/webhooks/demo"}],
            "http://emby",
            "key",
            "",
            "",
        )

    rows = (await db_session.execute(select(NotificationLog))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].error == "discord_rejected"


@pytest.mark.asyncio
async def test_system_notification_logs_failed_when_discord_rejects(db_session):
    await set_notification_channel(
        db_session,
        "discord",
        json.dumps({
            "enabled": True,
            "webhooks": [{
                "enabled": True,
                "name": "Main",
                "url": "https://discord.com/api/webhooks/demo",
                "events": {"offline": True},
            }],
        }),
    )

    with patch(
        "services.notification_engine.system.build_system_payload",
        new=AsyncMock(return_value={"content": "demo"}),
    ), patch(
        "services.notification_engine.system.send_discord_webhook",
        new=AsyncMock(return_value=False),
    ):
        await send_system_notification(db_session, "offline", {"title": "Emby offline"})

    rows = (await db_session.execute(select(NotificationLog).order_by(NotificationLog.id.asc()))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "offline"
    assert rows[0].status == "failed"
    assert rows[0].error == "discord_rejected"
