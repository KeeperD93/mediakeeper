"""A purge leaves the admin audit trail in place, but no longer saying who the person was."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from models.portal.audit import AdminAuditLog
from services.portal import admin_users_constants as constants
from services.portal import gdpr_erased
from services.portal.admin_users_audit import record_audit
from services.portal.admin_users_constants import (
    ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
    ACTION_DEBUG_XP_GRANTED,
    ACTION_DEBUG_ZONE_CORRECTION_PLAYER,
    ACTION_USER_CREATED,
    ACTION_USER_IMPORTED,
    ACTION_USER_NOTIFICATION_SENT,
    ACTION_USER_TAGS_UPDATED,
)
from services.portal.gdpr import purge_pending_deletions
from tests._gdpr_erased_helpers import gdpr_on, member

pytestmark = pytest.mark.asyncio

# Reviewed: what these actions store says nothing about who the person was.
NOTHING_PERSONAL = {
    constants.ACTION_USER_UPDATED_IDENTITY,
    constants.ACTION_USER_DISPLAY_NAME_RESET,
    constants.ACTION_USER_ROLE_CHANGED,
    constants.ACTION_USER_PERMISSIONS_CHANGED,
    constants.ACTION_USER_QUOTA_CHANGED,
    constants.ACTION_USER_ACCESS_WINDOW,
    constants.ACTION_USER_ACCESS_EXTENDED,
    constants.ACTION_USER_ACCESS_EXPIRED,
    constants.ACTION_USER_ACTIVATED,
    constants.ACTION_USER_DEACTIVATED,
    constants.ACTION_USER_EMBY_ENABLED,
    constants.ACTION_USER_EMBY_DISABLED,
    constants.ACTION_USER_PASSWORD_RESET,
    constants.ACTION_USER_NOTES_UPDATED,
    constants.ACTION_DEBUG_LEVEL_SET,
    constants.ACTION_DEBUG_ACHIEVEMENT_UNLOCKED,
    constants.ACTION_DEBUG_ACHIEVEMENT_LOCKED,
    constants.ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
    constants.ACTION_DEBUG_ACHIEVEMENT_RECHECK_ALL,
    constants.ACTION_DEBUG_ZONE_CORRECTION,
    constants.ACTION_SYSTEM_TIMEZONE_CHANGED,
    constants.ACTION_USER_RGPD_EXPORT,
    constants.ACTION_USER_SOFT_DELETED,
    constants.ACTION_USER_RESTORED,
    constants.ACTION_USER_BULK,
    constants.ACTION_USER_FORCE_LOGOUT,
    constants.ACTION_USER_DELETION_REQUEST_CANCELLED,
}

UNDO = {
    "trophies": {"night_owl": {"unlocked_at": "2026-01-01T23:30:00+00:00", "progress": 1}},
    "decorations": {"title_id": "night_owl"},
    "ledger": [{"id": 1, "reference": "achievement:night_owl", "xp": 50, "created_at": None}],
}


def _rows_about(name: str, guid: str) -> list[tuple[str, dict | None]]:
    return [
        (ACTION_USER_IMPORTED, {"emby_user_id": guid, "username": name}),
        (ACTION_USER_CREATED, {"username": name, "source": "local", "role": "admin"}),
        (ACTION_USER_TAGS_UPDATED, {"tags": [f"{name} family"]}),
        (ACTION_USER_NOTIFICATION_SENT, {"title": f"Hello {name}", "len": 12}),
        (ACTION_DEBUG_XP_GRANTED, {"delta": 50, "note": f"bonus for {name}", "xp": 50, "level": 2}),
        (ACTION_DEBUG_ZONE_CORRECTION_PLAYER, {
            "removed": ["night_owl"], "cascade": [], "xp_removed": 50,
            "xp": [100, 50], "level": [3, 2], "decorations": ["title_id"], "undo": UNDO,
        }),
        (ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, {"achievement_id": "night_owl"}),
    ]


async def _trail(db, user, guid: str) -> None:
    for action, payload in _rows_about(user.username, guid):
        await record_audit(
            db, admin_user_id=None, target_user_id=user.id, action=action, payload=payload, commit=False,
        )
    await db.commit()


async def _payloads(db, user_id: int) -> list[tuple[str, dict | None]]:
    query = (
        select(AdminAuditLog).where(AdminAuditLog.target_user_id == user_id).order_by(AdminAuditLog.id)
        .execution_options(populate_existing=True)
    )
    return [(row.action, row.payload) for row in (await db.execute(query)).scalars().all()]


async def test_the_trail_keeps_each_action_but_no_longer_who_they_were(db_session):
    await gdpr_on(db_session)
    alice = await member(db_session)
    await _trail(db_session, alice, "EMBY-ALICE")
    alice_id = alice.id

    assert await purge_pending_deletions(db_session) == 1

    assert await _payloads(db_session, alice_id) == [
        (ACTION_USER_IMPORTED, {}),
        (ACTION_USER_CREATED, {"source": "local", "role": "admin"}),
        (ACTION_USER_TAGS_UPDATED, {}),
        (ACTION_USER_NOTIFICATION_SENT, {"len": 12}),
        (ACTION_DEBUG_XP_GRANTED, {"delta": 50, "xp": 50, "level": 2}),
        (ACTION_DEBUG_ZONE_CORRECTION_PLAYER, {
            "removed": ["night_owl"], "cascade": [], "xp_removed": 50,
            "xp": [100, 50], "level": [3, 2], "decorations": ["title_id"],
        }),
        (ACTION_DEBUG_ACHIEVEMENT_UNLOCKED, {"achievement_id": "night_owl"}),
    ]


async def test_the_trail_of_someone_else_is_left_whole(db_session):
    await gdpr_on(db_session)
    await _trail(db_session, await member(db_session), "EMBY-ALICE")
    bob = await member(db_session, "bob", guid="EMBY-BOB", overdue=False)
    await _trail(db_session, bob, "EMBY-BOB")

    assert await purge_pending_deletions(db_session) == 1

    assert await _payloads(db_session, bob.id) == _rows_about("bob", "EMBY-BOB")


async def test_a_failed_deletion_leaves_the_trail_whole(db_session):
    await gdpr_on(db_session)
    alice = await member(db_session)
    await _trail(db_session, alice, "EMBY-ALICE")
    alice_id = alice.id

    with patch.object(db_session, "delete", new=AsyncMock(side_effect=RuntimeError("boom"))), \
         pytest.raises(RuntimeError):
        await purge_pending_deletions(db_session)
    await db_session.rollback()

    assert await _payloads(db_session, alice_id) == _rows_about("alice", "EMBY-ALICE")


async def test_the_trail_reaches_the_database_before_the_photos_go(db_session):
    await gdpr_on(db_session)
    alice = await member(db_session)
    await _trail(db_session, alice, "EMBY-ALICE")
    order, pending = [], []
    real = gdpr_erased._remove_person_from_audit

    async def trail(db, user_id):
        await real(db, user_id)
        order.append("trail")

    def photos(_):
        order.append("photos")
        pending.extend(db_session.dirty)

    with patch.object(gdpr_erased, "_remove_person_from_audit", new=trail), \
         patch.object(gdpr_erased, "delete_all_avatars", side_effect=photos):
        assert await purge_pending_deletions(db_session) == 1

    assert order == ["trail", "photos"]
    assert pending == []


async def test_the_profile_is_locked_before_the_trail_is_read(db_session):
    statements = []
    real = db_session.execute

    async def spying(statement, *args, **kwargs):
        statements.append(str(statement.compile(dialect=postgresql.dialect())))
        return await real(statement, *args, **kwargs)

    with patch.object(db_session, "execute", new=spying):
        await gdpr_erased._remove_person_from_audit(db_session, 1)

    lock, trail = statements
    assert "user_profiles" in lock and lock.rstrip().endswith("FOR UPDATE")
    assert "admin_audit_log" in trail


async def test_every_audit_action_is_classified():
    """A new action that copies something about the person must join the purge's table."""
    personal = set(gdpr_erased._PERSONAL_AUDIT_KEYS)
    actions = {value for name, value in vars(constants).items() if name.startswith("ACTION_")}
    assert actions == personal | NOTHING_PERSONAL
    assert not personal & NOTHING_PERSONAL


async def test_a_row_without_payload_stays_empty(db_session):
    await gdpr_on(db_session)
    alice = await member(db_session)
    await record_audit(db_session, admin_user_id=None, target_user_id=alice.id, action=ACTION_USER_IMPORTED)
    alice_id = alice.id

    assert await purge_pending_deletions(db_session) == 1

    assert await _payloads(db_session, alice_id) == [(ACTION_USER_IMPORTED, None)]
