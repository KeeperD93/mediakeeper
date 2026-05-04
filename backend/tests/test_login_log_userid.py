"""Verify that successful logins log the numeric user_id, not the username.

Failure paths intentionally keep the username clear so an admin can
spot enumeration / brute-force patterns from the rotated log file.
"""
import logging
from unittest.mock import AsyncMock, patch

import pytest

from core.security import hash_password
from models.user import User


@pytest.mark.asyncio
async def test_admin_login_success_logs_user_id_not_username(
    client, admin_user, caplog
):
    """The admin fixture creates a real ``admin`` user (the only username
    in the backoffice allowlist), so the success branch reaches the
    new ``user_id=`` log line."""
    with caplog.at_level(logging.INFO, logger="mediakeeper.api.auth"):
        resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "TestPassword123!"},
        )

    assert resp.status_code == 200, resp.text
    success_lines = [
        r.getMessage() for r in caplog.records
        if "[LOGIN] Success" in r.getMessage()
    ]
    assert success_lines, "expected a [LOGIN] Success line"
    for line in success_lines:
        assert f"user_id={admin_user.id}" in line
        assert "user=admin" not in line  # PII handle gone on success


@pytest.mark.asyncio
async def test_admin_login_failure_keeps_username_clear(client, caplog):
    """The FAILURE branch must keep the username clear for forensics."""
    with caplog.at_level(logging.WARNING, logger="mediakeeper.api.auth"):
        resp = await client.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "wrong"},
        )

    assert resp.status_code == 401
    failure_lines = [
        r.getMessage() for r in caplog.records
        if "[LOGIN] Failure" in r.getMessage()
    ]
    assert failure_lines, "expected a [LOGIN] Failure line"
    for line in failure_lines:
        assert "ghost" in line  # username preserved on failure


@pytest.mark.asyncio
async def test_portal_admin_success_logs_user_id_not_username(
    client, admin_user, caplog
):
    with patch(
        "api.auth.login.grant_portal_admin_session", new=AsyncMock()
    ):
        with caplog.at_level(logging.INFO, logger="mediakeeper.api.auth"):
            resp = await client.post(
                "/api/auth/portal-login",
                json={"username": "admin", "password": "TestPassword123!"},
            )

    assert resp.status_code == 200, resp.text
    success_lines = [
        r.getMessage() for r in caplog.records
        if "[PORTAL_LOGIN] Admin success" in r.getMessage()
    ]
    assert success_lines
    for line in success_lines:
        assert f"user_id={admin_user.id}" in line
        assert "user=admin" not in line


@pytest.mark.asyncio
async def test_portal_login_failure_keeps_username_clear(client, caplog):
    """Failure on the portal-login Emby branch keeps the username clear."""
    with caplog.at_level(logging.WARNING, logger="mediakeeper.api.auth"):
        resp = await client.post(
            "/api/auth/portal-login",
            json={"username": "ghost", "password": "wrong"},
        )

    assert resp.status_code == 401
    failure_lines = [
        r.getMessage() for r in caplog.records
        if "[PORTAL_LOGIN]" in r.getMessage()
        and "Requests failure" in r.getMessage()
    ]
    if failure_lines:
        for line in failure_lines:
            assert "ghost" in line
