"""Auth-scope Pydantic schemas reject unknown keys.

Defence-in-depth: a hostile client can't probe for hidden fields by
slipping extra keys past the validator, and a buggy client that
mistypes a field name (``passwd`` instead of ``password``) fails
loudly with 422 instead of being silently authenticated against the
remaining valid subset.

Four direct-Pydantic tests cover all four schemas in isolation, plus
one HTTP round-trip on ``/api/auth/login`` to assert the 422 surfaces
correctly to the operator without being shadowed by an earlier
auth/CSRF gate.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.auth._schemas import (
    ChangePasswordRequest,
    LocaleRequest,
    LoginRequest,
    PreferencesRequest,
)


def test_login_request_rejects_extra_key():
    with pytest.raises(ValidationError) as exc:
        LoginRequest.model_validate({
            "username": "admin",
            "password": "TestPassword123!",
            "remember_me": True,
        })
    assert "remember_me" in str(exc.value)


def test_change_password_request_rejects_extra_key():
    with pytest.raises(ValidationError) as exc:
        ChangePasswordRequest.model_validate({
            "current_password": "Old-Password-12!aa",
            "new_password": "New-Password-12!aa",
            "confirm_password": "New-Password-12!aa",
            "force_logout_others": True,
        })
    assert "force_logout_others" in str(exc.value)


def test_preferences_request_rejects_extra_key():
    with pytest.raises(ValidationError) as exc:
        PreferencesRequest.model_validate({
            "theme": "dark",
            "rogue_admin_flag": True,
        })
    assert "rogue_admin_flag" in str(exc.value)


def test_locale_request_rejects_extra_key():
    with pytest.raises(ValidationError) as exc:
        LocaleRequest.model_validate({
            "locale": "fr",
            "fallback": "en",
        })
    assert "fallback" in str(exc.value)


@pytest.mark.asyncio
async def test_login_endpoint_returns_422_on_extra_key(client):
    """Round-trip check: the extra=forbid rejection surfaces as a clean
    422 over HTTP, not a 500 or a silent 200."""
    resp = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "TestPassword123!",
        "leaked_secret_probe": "leak",
    })
    assert resp.status_code == 422, resp.text
    body = resp.json()
    payload = str(body)
    assert "leaked_secret_probe" in payload
