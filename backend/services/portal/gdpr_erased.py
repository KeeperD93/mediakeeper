"""What a GDPR purge does just before an account goes.

Who left is remembered, so that Emby identity is never given an account again: one
``settings`` row per fingerprint, no migration, nothing to lock, and a ZIP restore can
only add to them. A fingerprint keeps a name out of sight, not out of reach: whoever
holds the playback rows can compute it.

Their name comes off the rows that outlive the account, and their photo is deleted.
"""
import asyncio
import hashlib

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from constants.gdpr import GDPR_ERASED_KEY_PREFIX
from models.portal.feedback_report import FeedbackReport
from models.portal.profile import UserProfile
from models.portal.request import RequestBlacklist
from models.settings import Setting
from models.user import User
from services.portal.admin_users_constants import SOURCE_LOCAL
from services.portal.avatars import delete_avatar
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
    """By Emby id or by name: a name given to someone else on Emby is blocked too, or that
    person would read the erased person's plays (``playback_owner.played_by``). Creating a
    local account does not check it."""
    return not erased.isdisjoint(_identity_keys(emby_user_id, username))


async def _id_nobody_else_uses(db: AsyncSession, user_id: int, emby_user_id: str | None) -> str | None:
    """Blocking an id another profile still uses would drop that person's plays. The last
    profile to leave records it: this query flushes the deletions already made in the run."""
    if not emby_user_id:
        return None
    other = (await db.execute(
        select(UserProfile.id)
        .where(UserProfile.emby_user_id == emby_user_id, UserProfile.user_id != user_id)
        .limit(1)
    )).first()
    return None if other else emby_user_id


async def _remember_identity(db: AsyncSession, user: User) -> None:
    profile = (await db.execute(
        select(UserProfile.emby_user_id, UserProfile.source).where(UserProfile.user_id == user.id)
    )).first()
    # A local account has no Emby identity to remember, unless one was linked to it by name.
    if profile is None or (profile.source == SOURCE_LOCAL and not profile.emby_user_id):
        return
    emby_user_id = await _id_nobody_else_uses(db, user.id, profile.emby_user_id)
    keys = _identity_keys(emby_user_id, user.username)
    await set_settings_map(db, dict.fromkeys(keys, "1"), commit=False)


async def _remove_name_from_kept_rows(db: AsyncSession, user_id: int) -> None:
    """Moderation and the blacklist hold a copy of the name: the link to the account goes
    with the account, the copy would not. ``anonymous`` too, or a report validated later
    would be relayed under the admin's name (``feedback._report_author``)."""
    await db.execute(
        update(FeedbackReport)
        .where(FeedbackReport.reporter_user_id == user_id)
        .values(reporter_name=None, anonymous=True)
        .execution_options(synchronize_session="fetch")
    )
    blacklist = await db.execute(
        select(RequestBlacklist).with_for_update().execution_options(populate_existing=True)
    )
    for row in blacklist.scalars():
        kept = [entry for entry in row.requesters or [] if entry["user_id"] != user_id]
        if len(kept) != len(row.requesters or []):
            row.requesters = kept


async def _delete_photo(db: AsyncSession, user_id: int) -> None:
    """A file cannot be rolled back, so it goes before the commit: a purge that fails is
    retried, whereas a photo left by a crash after the commit could never be found again."""
    stored = (await db.execute(
        select(UserProfile.avatar_custom_path).where(UserProfile.user_id == user_id)
    )).scalar_one_or_none()
    await asyncio.to_thread(delete_avatar, stored)


async def prepare_erasure(db: AsyncSession, user: User) -> None:
    """Call just before deleting ``user``. The database writes stay in the caller's
    transaction: they leave with the deletion, or not at all. The photo goes last."""
    await _remember_identity(db, user)
    await _remove_name_from_kept_rows(db, user.id)
    await _delete_photo(db, user.id)
