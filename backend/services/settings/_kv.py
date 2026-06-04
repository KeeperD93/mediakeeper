"""Helpers CRUD : settings, user_preferences, watchlist_scans, notification_channels.

Sensitive keys (API keys, webhooks, passwords — see
``core.encryption.is_sensitive_key``) are encrypted with Fernet before being
stored and decrypted on read. Callers keep using plaintext — encryption is
transparent at this layer.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.encryption import ENCRYPTED_PREFIX, decrypt_value, encrypt_value, is_sensitive_key
from models.notification_channels import NotificationChannel
from models.settings import Setting
from models.user_preferences import UserPreference
from models.watchlist_scans import WatchlistScan


def _decode(key: str, value: str) -> str:
    if not value:
        return ""
    if is_sensitive_key(key):
        return decrypt_value(value)
    return value


def _encode(key: str, value: str) -> str:
    if not value:
        return ""
    if is_sensitive_key(key):
        return encrypt_value(value)
    return value


# settings (light config)
async def get_setting(db: AsyncSession, key: str) -> str:
    result = await db.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    return _decode(key, row.value) if row else ""


async def get_settings_map(db: AsyncSession, keys: list[str]) -> dict[str, str]:
    """Return several settings in a single query."""
    if not keys:
        return {}
    result = await db.execute(select(Setting).where(Setting.key.in_(keys)))
    rows = result.scalars().all()
    values = {row.key: _decode(row.key, row.value) for row in rows}
    return {key: values.get(key, "") for key in keys}


async def set_setting(db: AsyncSession, key: str, value: str, *, commit: bool = True):
    stored = _encode(key, value)
    result = await db.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = stored
    else:
        row = Setting(key=key, value=stored)
        db.add(row)
    if commit:
        await db.commit()
    else:
        await db.flush()


async def set_settings_map(
    db: AsyncSession,
    values: dict[str, str],
    *,
    commit: bool = True,
) -> None:
    """Create/update several settings with a single commit."""
    if not values:
        return
    result = await db.execute(select(Setting).where(Setting.key.in_(list(values.keys()))))
    existing_rows = {row.key: row for row in result.scalars().all()}
    for key, value in values.items():
        stored = _encode(key, value)
        row = existing_rows.get(key)
        if row:
            row.value = stored
        else:
            db.add(Setting(key=key, value=stored))
    if commit:
        await db.commit()
    else:
        await db.flush()


async def get_all_settings(
    db: AsyncSession,
    *,
    decrypt_sensitive: bool = False,
) -> dict:
    """Return every setting as a ``{key: value}`` mapping.

    Sensitive values stay encrypted by default (fail-safe): a caller that
    genuinely needs plaintext secrets must opt in with
    ``decrypt_sensitive=True``, so an accidental dump of the result cannot
    leak Fernet-decrypted API keys / passwords to an HTTP response.
    """
    result = await db.execute(select(Setting))
    rows = result.scalars().all()
    if decrypt_sensitive:
        return {r.key: _decode(r.key, r.value) for r in rows}
    return {r.key: r.value for r in rows}


async def encrypt_legacy_sensitive_values(
    db: AsyncSession,
    *,
    commit: bool = True,
) -> dict[str, int]:
    """Encrypt legacy cleartext secrets left by pre-Fernet installs."""
    settings_count = 0
    result = await db.execute(select(Setting))
    for row in result.scalars().all():
        if (
            row.value
            and is_sensitive_key(row.key)
            and not row.value.startswith(ENCRYPTED_PREFIX)
        ):
            row.value = encrypt_value(row.value)
            settings_count += 1

    channels_count = 0
    result = await db.execute(select(NotificationChannel))
    for row in result.scalars().all():
        if row.data and not row.data.startswith(ENCRYPTED_PREFIX):
            row.data = encrypt_value(row.data)
            channels_count += 1

    if settings_count or channels_count:
        if commit:
            await db.commit()
        else:
            await db.flush()
    return {"settings": settings_count, "notification_channels": channels_count}


# user_preferences
async def get_user_preferences(db: AsyncSession, user_id: int) -> UserPreference | None:
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    return result.scalar_one_or_none()


async def get_portal_default_language(db: AsyncSession, default: str | None = None) -> str:
    """Instance-wide default portal language (settings key
    ``portal.default_language``). A NULL ``user_profiles.language`` inherits it.
    Falls back to ``default`` then ``MK_DEFAULT_LOCALE``."""
    from core.i18n import DEFAULT_LOCALE, normalize_locale
    raw = await get_setting(db, "portal.default_language")
    return normalize_locale(raw) or normalize_locale(default) or DEFAULT_LOCALE


async def upsert_user_preferences(
    db: AsyncSession,
    user_id: int,
    preferences: str | None = None,
    dashboard_layout: str | None = None,
    *,
    commit: bool = True,
):
    row = await get_user_preferences(db, user_id)
    if not row:
        row = UserPreference(user_id=user_id)
        db.add(row)
    if preferences is not None:
        row.preferences = preferences
    if dashboard_layout is not None:
        row.dashboard_layout = dashboard_layout
    if commit:
        await db.commit()
    else:
        await db.flush()
    return row


# watchlist_scans
async def get_watchlist_data(db: AsyncSession, scan_key: str) -> str:
    result = await db.execute(select(WatchlistScan).where(WatchlistScan.scan_key == scan_key))
    row = result.scalar_one_or_none()
    return row.data if row else ""


async def set_watchlist_data(db: AsyncSession, scan_key: str, data: str, *, commit: bool = True):
    result = await db.execute(select(WatchlistScan).where(WatchlistScan.scan_key == scan_key))
    row = result.scalar_one_or_none()
    if row:
        row.data = data
    else:
        row = WatchlistScan(scan_key=scan_key, data=data)
        db.add(row)
    if commit:
        await db.commit()
    else:
        await db.flush()


# notification_channels
async def get_notification_channel(db: AsyncSession, channel_key: str) -> str:
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.channel_key == channel_key))
    row = result.scalar_one_or_none()
    return decrypt_value(row.data) if row else ""


async def set_notification_channel(
    db: AsyncSession,
    channel_key: str,
    data: str,
    *,
    commit: bool = True,
):
    stored = encrypt_value(data)
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.channel_key == channel_key))
    row = result.scalar_one_or_none()
    if row:
        row.data = stored
    else:
        row = NotificationChannel(channel_key=channel_key, data=stored)
        db.add(row)
    if commit:
        await db.commit()
    else:
        await db.flush()
