"""Custom avatar upload + delete coverage."""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
import pytest_asyncio

from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


@pytest_asyncio.fixture
async def avatar_storage(workspace_tmp_path):
    avatars_dir = workspace_tmp_path / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    with patch("services.portal.avatars.AVATAR_DIR", avatars_dir):
        yield avatars_dir


@pytest.mark.asyncio
async def test_avatar_upload_replaces_emby_url(client, db_session, avatar_storage):
    user, profile = await make_portal_user(
        db_session, username="alice", display_name="Alice",
    )
    profile.avatar_url = "/api/emby/user-image/EMBY123"
    db_session.add(profile)
    await db_session.commit()

    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    payload = io.BytesIO(b"\x89PNG\r\n\x1a\nfake-png-bytes")
    resp = await client.post(
        "/api/portal/profiles/me/avatar",
        files={"file": ("avatar.png", payload, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["avatar_url"].startswith("/api/portal/avatars/")
    assert body["avatar_custom_path"].endswith(".png")
    assert (avatar_storage / body["avatar_custom_path"]).exists()


@pytest.mark.asyncio
async def test_avatar_upload_rejects_bad_extension(client, db_session, avatar_storage):
    user, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    payload = io.BytesIO(b"not really a script")
    resp = await client.post(
        "/api/portal/profiles/me/avatar",
        files={"file": ("hack.exe", payload, "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "avatar_extension_not_allowed"


@pytest.mark.asyncio
async def test_avatar_upload_rejects_fake_image(client, db_session, avatar_storage):
    user, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    resp = await client.post(
        "/api/portal/profiles/me/avatar",
        files={"file": ("avatar.png", io.BytesIO(b"not-a-real-image"), "image/png")},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "avatar_invalid_image"
    assert list(avatar_storage.iterdir()) == []


@pytest.mark.asyncio
async def test_avatar_delete_falls_back_to_emby(client, db_session, avatar_storage):
    user, profile = await make_portal_user(db_session, username="alice")
    profile.avatar_url = "/api/emby/user-image/EMBY123"
    db_session.add(profile)
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    payload = io.BytesIO(b"\x89PNG\r\n\x1a\nfake")
    upload = await client.post(
        "/api/portal/profiles/me/avatar",
        files={"file": ("a.png", payload, "image/png")},
    )
    stored = upload.json()["avatar_custom_path"]
    assert (avatar_storage / stored).exists()

    delete = await client.delete("/api/portal/profiles/me/avatar")
    assert delete.status_code == 200
    body = delete.json()
    assert body["avatar_custom_path"] is None
    assert body["avatar_url"] == "/api/emby/user-image/EMBY123"
    assert not (avatar_storage / stored).exists()


@pytest.mark.asyncio
async def test_avatar_upload_replaces_previous_custom_file(
    client, db_session, avatar_storage,
):
    user, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))

    first = await client.post(
        "/api/portal/profiles/me/avatar",
        files={"file": ("a.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfirst"), "image/png")},
    )
    first_name = first.json()["avatar_custom_path"]

    second = await client.post(
        "/api/portal/profiles/me/avatar",
        files={"file": ("b.png", io.BytesIO(b"\x89PNG\r\n\x1a\nsecond"), "image/png")},
    )
    second_name = second.json()["avatar_custom_path"]

    assert first_name != second_name
    assert not (avatar_storage / first_name).exists()
    assert (avatar_storage / second_name).exists()
