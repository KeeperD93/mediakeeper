"""Who a GDPR purge erased: that Emby identity is never given an account again.

One ``settings`` row per fingerprint: no migration, nothing to lock, and a restore can
only add to them. A fingerprint keeps a name out of sight, not out of reach: whoever
holds the playback rows can compute it.
"""
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.gdpr import GDPR_ERASED_KEY_PREFIX
from models.portal.profile import UserProfile
from models.settings import Setting
from models.user import User
from services.portal.admin_users_constants import SOURCE_LOCAL
from services.settings import set_settings_map


def _key(kind: str, value: str) -> str:
    return GDPR_ERASED_KEY_PREFIX + hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()


def _identity_keys(emby_user_id: str | None, username: str | None) -> set[str]:
    keys = set()
    if emby_user_id:
        keys.add(_key("id", emby_user_id))
    name = (username or "").strip().lower()
    if name:
        keys.add(_key("name", name))
    return keys


async def load_erased_identities(db: AsyncSession) -> frozenset[str]:
    rows = await db.execute(select(Setting.key).where(Setting.key.startswith(GDPR_ERASED_KEY_PREFIX)))
    return frozenset(rows.scalars())


def is_erased(erased: frozenset[str], emby_user_id: str | None, username: str | None) -> bool:
    """By Emby id or by name: a name given to someone else is blocked too, or that person
    would read the erased person's plays (``playback_owner.played_by``)."""
    return not erased.isdisjoint(_identity_keys(emby_user_id, username))


async def remember_erased_identity(db: AsyncSession, user: User) -> None:
    """Record an account about to be purged, in the caller's transaction."""
    profile = (await db.execute(
        select(UserProfile.emby_user_id, UserProfile.source).where(UserProfile.user_id == user.id)
    )).first()
    # A local account has no Emby identity to remember, unless one was linked to it by name.
    if profile is None or (profile.source == SOURCE_LOCAL and not profile.emby_user_id):
        return
    keys = _identity_keys(profile.emby_user_id, user.username)
    await set_settings_map(db, dict.fromkeys(keys, "1"), commit=False)
