import json
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


@pytest.mark.asyncio
async def test_create_folders_batch_rejects_parent_escape(monkeypatch, tmp_path):
    """Folder escape via '..' component is refused by the barrier guard."""
    from services.media_manager import categories as cat_module
    from services.media_manager import move as move_service

    media_root = tmp_path / "media-root"
    series_root = media_root / "Series"
    series_root.mkdir(parents=True)
    monkeypatch.setattr(
        cat_module,
        "_categories_cache",
        [{"key": "media", "label": "media", "path": str(media_root.resolve())}],
    )

    payload = await move_service.create_folders_batch([
        {"parent_path": str(series_root), "folder_name": "../outside"},
    ])

    assert payload["results"][0]["error"] in {"name_not_allowed", "path_not_allowed"}
    assert not (media_root / "outside").exists()


@pytest.mark.asyncio
async def test_create_folders_batch_still_creates_valid_child(monkeypatch, tmp_path):
    """A legitimate child folder name is created under the parent."""
    from services.media_manager import categories as cat_module
    from services.media_manager import move as move_service

    media_root = tmp_path / "media-root"
    series_root = media_root / "Series"
    series_root.mkdir(parents=True)
    monkeypatch.setattr(
        cat_module,
        "_categories_cache",
        [{"key": "media", "label": "media", "path": str(media_root.resolve())}],
    )

    payload = await move_service.create_folders_batch([
        {"parent_path": str(series_root), "folder_name": "Season 01"},
    ])

    assert payload["results"][0]["success"] is True
    assert (series_root / "Season 01").is_dir()


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

    # A non-owner is denied without leaking the ticket's existence: 404,
    # not 403 (#422).
    assert resp.status_code == 404
    assert resp.json()["detail"] == "ticket_not_found"


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
