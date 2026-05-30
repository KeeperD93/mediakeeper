"""get_all_settings keeps sensitive values encrypted by default (fail-safe).

A caller must opt into ``decrypt_sensitive=True`` to receive plaintext
secrets, so an accidental dump of the mapping cannot leak Fernet-decrypted
API keys / passwords to an HTTP response.
"""
from __future__ import annotations

import pytest

from core.encryption import ENCRYPTED_PREFIX
from services.settings._kv import get_all_settings, set_setting


@pytest.mark.asyncio
async def test_get_all_settings_keeps_secrets_encrypted_by_default(db_session):
    await set_setting(db_session, "emby.api_key", "super-secret-key")

    default = await get_all_settings(db_session)
    assert default["emby.api_key"].startswith(ENCRYPTED_PREFIX)
    assert "super-secret-key" not in default["emby.api_key"]

    decrypted = await get_all_settings(db_session, decrypt_sensitive=True)
    assert decrypted["emby.api_key"] == "super-secret-key"
