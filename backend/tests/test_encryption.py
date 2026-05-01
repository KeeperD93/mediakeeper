"""Fernet encryption for sensitive settings."""

import pytest
from sqlalchemy import select

from core.encryption import (
    ENCRYPTED_PREFIX,
    PersistentFernetKey,
    decrypt_value,
    encrypt_value,
    get_persistent_fernet_key,
    is_sensitive_key,
)
from models.settings import Setting
from models.notification_channels import NotificationChannel
from services.settings import (
    encrypt_legacy_sensitive_values,
    get_notification_channel,
    get_setting,
    set_setting,
)


def test_is_sensitive_key_detects_known_suffixes():
    assert is_sensitive_key("emby.api_key")
    assert is_sensitive_key("opensubtitles.password")
    assert is_sensitive_key("discord.webhook_url")
    assert is_sensitive_key("some.provider.token")
    assert is_sensitive_key("some.service.secret")

    assert not is_sensitive_key("emby.url")
    assert not is_sensitive_key("dashboard.layout")
    assert not is_sensitive_key("")


def test_encrypt_decrypt_roundtrip():
    plain = "my-very-secret-api-key-abc123"
    cipher = encrypt_value(plain)
    assert cipher.startswith(ENCRYPTED_PREFIX)
    assert cipher != plain
    assert decrypt_value(cipher) == plain


def test_decrypt_passthrough_on_plaintext():
    assert decrypt_value("plain-value") == "plain-value"
    assert decrypt_value("") == ""


def test_encrypt_empty_stays_empty():
    assert encrypt_value("") == ""


def test_get_persistent_fernet_key_prefers_env(monkeypatch, tmp_path):
    other = tmp_path / "encryption_key"
    other.write_text("file-key", encoding="ascii")
    monkeypatch.setenv("MEDIAKEEPER_ENCRYPTION_KEY", "env-key")
    monkeypatch.setattr("core.encryption._KEY_FILE_PATHS", (other,))

    resolved = get_persistent_fernet_key()
    assert isinstance(resolved, PersistentFernetKey)
    assert resolved.key == "env-key"
    assert resolved.source == "env"
    assert resolved.path is None


def test_get_persistent_fernet_key_falls_back_to_file(monkeypatch, tmp_path):
    target = tmp_path / "encryption_key"
    target.write_text("file-key", encoding="ascii")
    monkeypatch.delenv("MEDIAKEEPER_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr("core.encryption._KEY_FILE_PATHS", (target,))

    resolved = get_persistent_fernet_key()
    assert resolved is not None
    assert resolved.key == "file-key"
    assert resolved.source == "file"
    assert resolved.path == str(target)


def test_get_persistent_fernet_key_returns_none_when_ephemeral(monkeypatch, tmp_path):
    monkeypatch.delenv("MEDIAKEEPER_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr("core.encryption._KEY_FILE_PATHS", (tmp_path / "missing",))

    assert get_persistent_fernet_key() is None


def test_encrypt_idempotent_on_already_encrypted():
    plain = "token-xyz"
    once = encrypt_value(plain)
    twice = encrypt_value(once)
    assert once == twice


@pytest.mark.asyncio
async def test_set_setting_encrypts_sensitive_key_at_rest(db_session):
    await set_setting(db_session, "emby.api_key", "super-secret")
    stored = (
        await db_session.execute(
            select(Setting.value).where(Setting.key == "emby.api_key")
        )
    ).scalar_one()
    assert stored.startswith(ENCRYPTED_PREFIX), "raw DB value must be encrypted"
    assert "super-secret" not in stored

    decoded = await get_setting(db_session, "emby.api_key")
    assert decoded == "super-secret"


@pytest.mark.asyncio
async def test_set_setting_leaves_non_sensitive_key_plain(db_session):
    await set_setting(db_session, "emby.url", "http://emby.local:8096")
    stored = (
        await db_session.execute(
            select(Setting.value).where(Setting.key == "emby.url")
        )
    ).scalar_one()
    assert stored == "http://emby.local:8096"


@pytest.mark.asyncio
async def test_encrypt_legacy_sensitive_values_migrates_plaintext_rows(db_session):
    db_session.add(Setting(key="tmdb.api_key", value="legacy-key"))
    db_session.add(Setting(key="emby.url", value="http://emby.local:8096"))
    db_session.add(NotificationChannel(channel_key="discord", data='{"url":"legacy-webhook"}'))
    await db_session.commit()

    migrated = await encrypt_legacy_sensitive_values(db_session)

    assert migrated == {"settings": 1, "notification_channels": 1}
    stored_key = (
        await db_session.execute(
            select(Setting.value).where(Setting.key == "tmdb.api_key")
        )
    ).scalar_one()
    stored_url = (
        await db_session.execute(
            select(Setting.value).where(Setting.key == "emby.url")
        )
    ).scalar_one()
    stored_channel = (
        await db_session.execute(
            select(NotificationChannel.data).where(NotificationChannel.channel_key == "discord")
        )
    ).scalar_one()

    assert stored_key.startswith(ENCRYPTED_PREFIX)
    assert stored_channel.startswith(ENCRYPTED_PREFIX)
    assert stored_url == "http://emby.local:8096"
    assert await get_setting(db_session, "tmdb.api_key") == "legacy-key"
    assert await get_notification_channel(db_session, "discord") == '{"url":"legacy-webhook"}'
