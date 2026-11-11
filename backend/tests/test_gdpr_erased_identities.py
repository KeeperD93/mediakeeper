"""Someone erased at their request never gets an account back and is no longer recorded."""
import json
import logging
import zipfile
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession
from models.user import User
from services.backup import restore as restore_module
from services.portal import gdpr as gdpr_module
from services.portal.admin_users_constants import SOURCE_LOCAL
from services.portal.admin_users_emby import (
    import_selected_emby_users,
    list_unimported_emby_users,
)
from services.portal.gdpr import cancel_deletion_request, purge_pending_deletions
from services.portal.gdpr_erased import (
    _identity_keys,
    is_erased,
    load_erased_identities,
)
from services.portal.user_import import ensure_user_for_emby_session
from services.settings import get_all_settings, set_setting
from services.stats_collector.collect import _grant_post_session_xp
from tests._gdpr_erased_helpers import GUID, gdpr_on, member, purged

pytestmark = pytest.mark.asyncio

TICK = 10_000_000
EMBY_USERS = [{"Id": GUID, "Name": "alice"}, {"Id": "EMBY-BOB", "Name": "bob"}]


async def _names(db) -> list[str]:
    return sorted((await db.execute(select(User.username))).scalars().all())


async def _see(db, name, guid):
    return await ensure_user_for_emby_session(db, emby_username=name, emby_user_id=guid)


def _archive(folder, settings: dict):
    path = folder / "restore.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps(settings))
    return path


async def test_an_erased_person_who_keeps_watching_gets_no_account_and_earns_nothing(db_session):
    await purged(db_session)
    now = datetime.now(UTC)
    play = PlaybackSession(
        session_key=f"{GUID}_1", user_id=GUID, user_name="alice", item_id="movie-1", item_name="Test Movie",
        item_type="Movie", duration_ticks=7200 * TICK, position_ticks=7000 * TICK,
        started_at=now - timedelta(minutes=5), ended_at=now, is_active=False,
    )
    db_session.add(play)
    await db_session.commit()
    check = AsyncMock(return_value=[])

    with patch("services.portal.achievements.check_all_achievements", new=check):
        await _grant_post_session_xp(db_session, [play])

    assert await _names(db_session) == []
    check.assert_not_awaited()


@pytest.mark.parametrize(("name", "guid"), [
    ("renamed", GUID),
    ("alice", "EMBY-NEW"),
    ("ALICE", "EMBY-NEW"),
    ("alice", None),
])
async def test_the_emby_id_or_the_name_is_enough_to_recognise_them(db_session, name, guid):
    await purged(db_session)
    assert await _see(db_session, name, guid) is None
    assert await _names(db_session) == []


async def test_a_profile_without_an_emby_id_is_remembered_by_its_name(db_session):
    await purged(db_session, guid=None)
    assert await _see(db_session, "Alice", "EMBY-ANY") is None


async def test_a_local_account_leaves_nothing_to_remember(db_session):
    await purged(db_session, "dave", guid=None, source=SOURCE_LOCAL)
    assert await load_erased_identities(db_session) == frozenset()
    assert await _see(db_session, "dave", "EMBY-DAVE") is not None


async def test_a_local_account_linked_to_emby_is_remembered(db_session):
    await purged(db_session, "dave", guid="EMBY-DAVE", source=SOURCE_LOCAL)
    assert await _see(db_session, "dave", "EMBY-DAVE") is None


async def test_someone_else_still_gets_an_account(db_session):
    await purged(db_session)
    assert (await _see(db_session, "bob", "EMBY-BOB")).username == "bob"


async def test_the_other_profile_of_a_shared_emby_id_keeps_its_account(db_session):
    await gdpr_on(db_session)
    await member(db_session, "alice-old")
    kept = await member(db_session, "alice-new", overdue=False)
    assert await purge_pending_deletions(db_session) == 1
    assert (await _see(db_session, "alice", GUID)).id == kept.id


async def test_turning_the_privacy_mode_off_forgets_nobody(db_session):
    await purged(db_session)
    await set_setting(db_session, "gdpr.enabled", "false")
    assert await _see(db_session, "alice", GUID) is None


async def test_a_cancelled_request_remembers_nothing(db_session):
    await gdpr_on(db_session)
    await cancel_deletion_request(db_session, await member(db_session))
    assert await purge_pending_deletions(db_session) == 0
    assert await load_erased_identities(db_session) == frozenset()


async def test_nothing_is_remembered_while_the_privacy_mode_is_off(db_session):
    await member(db_session)
    assert await purge_pending_deletions(db_session) == 0
    assert await load_erased_identities(db_session) == frozenset()


async def test_two_people_erased_in_one_run_are_both_remembered(db_session):
    await gdpr_on(db_session)
    await member(db_session, "alice", guid="EMBY-A")
    await member(db_session, "bob", guid="EMBY-B")
    assert await purge_pending_deletions(db_session) == 2
    erased = await load_erased_identities(db_session)
    assert is_erased(erased, "EMBY-A", None) and is_erased(erased, "EMBY-B", None)


async def test_two_profiles_of_one_emby_id_can_be_purged_together(db_session):
    await gdpr_on(db_session)
    await member(db_session, "alice")
    await member(db_session, "alice-bis")
    assert await purge_pending_deletions(db_session) == 2
    assert is_erased(await load_erased_identities(db_session), GUID, None)


async def test_an_id_someone_else_still_uses_is_not_remembered(db_session):
    await gdpr_on(db_session)
    await member(db_session, "alice-old")
    await member(db_session, "alice-new", overdue=False)
    assert await purge_pending_deletions(db_session) == 1
    erased = await load_erased_identities(db_session)
    assert not is_erased(erased, GUID, None) and is_erased(erased, None, "alice-old")


async def test_the_last_profile_of_a_shared_id_remembers_it(db_session):
    await gdpr_on(db_session)
    await member(db_session, "alice-old")
    last = await member(db_session, "alice-new", overdue=False)
    await purge_pending_deletions(db_session)
    last.pending_deletion_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()
    assert await purge_pending_deletions(db_session) == 1
    assert is_erased(await load_erased_identities(db_session), GUID, None)


async def test_a_failed_deletion_remembers_nothing(db_session):
    await gdpr_on(db_session)
    await member(db_session)
    with patch.object(db_session, "delete", new=AsyncMock(side_effect=RuntimeError("boom"))), \
         pytest.raises(RuntimeError):
        await purge_pending_deletions(db_session)
    await db_session.rollback()
    assert await load_erased_identities(db_session) == frozenset()
    assert await _names(db_session) == ["alice"]


async def test_a_person_who_cannot_be_remembered_is_not_purged(db_session):
    await gdpr_on(db_session)
    await member(db_session)
    with patch.object(gdpr_module, "prepare_erasure", new=AsyncMock(side_effect=RuntimeError("boom"))), \
         pytest.raises(RuntimeError):
        await purge_pending_deletions(db_session)
    await db_session.rollback()
    assert await _names(db_session) == ["alice"]


async def test_a_commit_between_two_people_keeps_each_fingerprint_with_its_deletion(db_session):
    await gdpr_on(db_session)
    await member(db_session, "alice", guid="EMBY-A")
    await member(db_session, "bob", guid="EMBY-B")
    prepare = gdpr_module.prepare_erasure

    async def commits(session, _user_id):
        await session.commit()

    async def fails_for_bob(session, user):
        if user.username == "bob":
            raise RuntimeError("boom")
        await prepare(session, user)

    with patch.object(gdpr_module, "_cancel_scheduled_mk_events", new=commits), \
         patch.object(gdpr_module, "prepare_erasure", new=fails_for_bob), \
         pytest.raises(RuntimeError):
        await purge_pending_deletions(db_session)
    await db_session.rollback()

    erased = await load_erased_identities(db_session)
    assert is_erased(erased, "EMBY-A", None) and not is_erased(erased, "EMBY-B", None)
    assert await _names(db_session) == ["bob"]


async def test_the_import_window_leaves_them_out(db_session):
    await purged(db_session)
    with patch("services.portal.admin_users_emby.list_emby_users", new=AsyncMock(return_value=EMBY_USERS)):
        result = await list_unimported_emby_users(db_session)
    assert [item["username"] for item in result["items"]] == ["bob"]
    assert result["total_emby"] == 2


async def test_an_import_naming_them_skips_them(db_session):
    await purged(db_session)
    with patch("services.portal.admin_users_emby.list_emby_users", new=AsyncMock(return_value=EMBY_USERS)):
        result = await import_selected_emby_users(
            db_session, emby_user_ids=[GUID, "EMBY-BOB"], admin_user_id=None,
        )
    assert result == {"ok": True, "created": 1, "skipped": 1}
    assert await _names(db_session) == ["bob"]


async def test_a_restore_forgets_nobody(db_session, workspace_tmp_path):
    await purged(db_session)
    before = await load_erased_identities(db_session)
    path = _archive(workspace_tmp_path, {"restore.key": "after"})

    await restore_module.restore_backup(db_session, path, components={"settings": True})

    assert before and await load_erased_identities(db_session) == before


async def test_an_archive_adds_the_people_it_remembers(db_session, workspace_tmp_path):
    key = next(iter(_identity_keys("EMBY-OLD", None)))
    path = _archive(workspace_tmp_path, {key: "1"})

    await restore_module.restore_backup(db_session, path, components={"settings": True})

    assert is_erased(await load_erased_identities(db_session), "EMBY-OLD", None)


async def test_a_blank_identity_matches_nothing():
    assert _identity_keys("", "  ") == set()
    assert not is_erased(frozenset(_identity_keys("EMBY-A", "alice")), "", "  ")


async def test_capitals_outside_a_to_z_are_folded():
    assert _identity_keys(None, "Émile") == _identity_keys(None, "émile")


async def test_the_settings_hold_neither_name_nor_emby_id(db_session):
    await purged(db_session)
    dumped = json.dumps(await get_all_settings(db_session))
    assert "gdpr.erased." in dumped
    assert "alice" not in dumped and GUID not in dumped


async def test_the_purge_log_names_nobody(db_session, caplog):
    with caplog.at_level(logging.INFO, logger="mediakeeper.portal.gdpr"):
        await purged(db_session)
    assert "purging" in caplog.text
    assert "alice" not in caplog.text
