"""Shared setup for the tests of what a GDPR purge leaves behind. Fictional data only."""
from datetime import UTC, datetime, timedelta

from models.portal.profile import UserProfile
from models.user import User
from services.portal.admin_users_constants import SOURCE_EMBY
from services.portal.gdpr import purge_pending_deletions
from services.settings import set_setting

GUID = "EMBY-ALICE"


async def gdpr_on(db) -> None:
    await set_setting(db, "gdpr.enabled", "true")


async def member(db, name="alice", *, guid=GUID, source=SOURCE_EMBY, overdue=True) -> User:
    past = datetime.now(UTC) - timedelta(hours=1) if overdue else None
    user = User(
        username=name, hashed_password="x", is_active=True, must_change_password=False,
        deletion_requested_at=past, pending_deletion_at=past,
    )
    db.add(user)
    await db.flush()
    db.add(UserProfile(
        user_id=user.id, display_name=name, role="viewer", source=source,
        account_active=True, emby_user_id=guid,
    ))
    await db.commit()
    return user


async def purged(db, name="alice", *, guid=GUID, source=SOURCE_EMBY) -> None:
    await gdpr_on(db)
    await member(db, name, guid=guid, source=source)
    assert await purge_pending_deletions(db) == 1
