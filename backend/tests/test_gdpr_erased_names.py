"""A purge takes the person's name off what outlives the account, and deletes their photo."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, update

from models.portal.feedback_report import FeedbackReport
from models.portal.profile import UserProfile
from models.portal.request import RequestBlacklist
from services.feedback import _report_author
from services.portal import gdpr_erased
from services.portal.admin_users_constants import SOURCE_LOCAL
from services.portal.gdpr import purge_pending_deletions
from tests._gdpr_erased_helpers import gdpr_on, member

pytestmark = pytest.mark.asyncio


async def _report(db, user, name: str) -> None:
    db.add(FeedbackReport(
        reporter_user_id=user.id, reporter_name=name, title="Test", description="Test", anonymous=False,
    ))
    await db.commit()


async def _reports(db) -> list[FeedbackReport]:
    query = select(FeedbackReport).order_by(FeedbackReport.id).execution_options(populate_existing=True)
    return list((await db.execute(query)).scalars().all())


async def _blocked(db, tmdb_id: int, *requesters) -> None:
    db.add(RequestBlacklist(
        tmdb_id=tmdb_id, media_type="movie", title="Test Movie",
        requesters=[{"user_id": user.id, "display_name": user.username} for user in requesters] or None,
    ))
    await db.commit()


async def _requesters(db) -> list[list | None]:
    query = select(RequestBlacklist).order_by(RequestBlacklist.tmdb_id).execution_options(populate_existing=True)
    return [row.requesters for row in (await db.execute(query)).scalars().all()]


async def _photo(db, folder, user):
    stored = f"{user.id}_1.png"
    await db.execute(update(UserProfile).where(UserProfile.user_id == user.id).values(avatar_custom_path=stored))
    await db.commit()
    path = folder / stored
    path.write_bytes(b"test")
    return path


async def test_all_their_photos_are_deleted_and_nobody_elses(db_session, workspace_tmp_path):
    await gdpr_on(db_session)
    alice = await member(db_session)
    gone = await _photo(db_session, workspace_tmp_path, alice)
    left_by_a_failed_upload = workspace_tmp_path / f"{alice.id}_2.png"
    left_by_a_failed_upload.write_bytes(b"test")
    bob = await member(db_session, "bob", guid="EMBY-BOB", overdue=False)
    kept = await _photo(db_session, workspace_tmp_path, bob)
    id_starting_with_hers = workspace_tmp_path / f"{alice.id}0_1.png"
    id_starting_with_hers.write_bytes(b"test")

    with patch("services.portal.avatars.AVATAR_DIR", workspace_tmp_path):
        assert await purge_pending_deletions(db_session) == 1

    assert not gone.exists() and not left_by_a_failed_upload.exists()
    assert kept.exists() and id_starting_with_hers.exists()


async def test_a_photo_that_cannot_be_deleted_stops_the_purge_until_it_can(db_session, workspace_tmp_path):
    await gdpr_on(db_session)
    photo = await _photo(db_session, workspace_tmp_path, await member(db_session))

    with patch("services.portal.avatars.AVATAR_DIR", workspace_tmp_path):
        with patch("services.portal.avatars.Path.unlink", side_effect=PermissionError("locked")), \
             pytest.raises(PermissionError):
            await purge_pending_deletions(db_session)
        await db_session.rollback()
        assert photo.exists()
        assert await purge_pending_deletions(db_session) == 1
    assert not photo.exists()


async def test_a_folder_that_cannot_be_read_stops_the_purge_until_it_can(db_session, workspace_tmp_path):
    await gdpr_on(db_session)
    photo = await _photo(db_session, workspace_tmp_path, await member(db_session))

    with patch("services.portal.avatars.AVATAR_DIR", workspace_tmp_path):
        with patch("os.scandir", side_effect=PermissionError("denied")), pytest.raises(PermissionError):
            await purge_pending_deletions(db_session)
        await db_session.rollback()
        assert await purge_pending_deletions(db_session) == 1
    assert not photo.exists()


async def test_the_photo_stays_when_a_database_step_fails_first(db_session, workspace_tmp_path):
    await gdpr_on(db_session)
    photo = await _photo(db_session, workspace_tmp_path, await member(db_session))

    with patch("services.portal.avatars.AVATAR_DIR", workspace_tmp_path), \
         patch.object(gdpr_erased, "_remove_name_from_kept_rows", new=AsyncMock(side_effect=RuntimeError("boom"))), \
         pytest.raises(RuntimeError):
        await purge_pending_deletions(db_session)
    await db_session.rollback()

    assert photo.exists()


async def test_a_purge_that_fails_after_the_photo_is_retried(db_session, workspace_tmp_path):
    await gdpr_on(db_session)
    photo = await _photo(db_session, workspace_tmp_path, await member(db_session))

    with patch("services.portal.avatars.AVATAR_DIR", workspace_tmp_path):
        with patch.object(db_session, "delete", new=AsyncMock(side_effect=RuntimeError("boom"))), \
             pytest.raises(RuntimeError):
            await purge_pending_deletions(db_session)
        await db_session.rollback()
        assert not photo.exists()
        assert await purge_pending_deletions(db_session) == 1


async def test_moderation_no_longer_shows_their_name(db_session):
    await gdpr_on(db_session)
    await _report(db_session, await member(db_session), "alice")
    await _report(db_session, await member(db_session, "bob", guid="EMBY-BOB", overdue=False), "bob")

    assert await purge_pending_deletions(db_session) == 1

    erased, other = await _reports(db_session)
    assert (erased.reporter_user_id, erased.reporter_name, erased.anonymous) == (None, None, True)
    assert (other.reporter_name, other.anonymous) == ("bob", False)


async def test_a_report_validated_afterwards_is_relayed_as_anonymous(db_session):
    await gdpr_on(db_session)
    await _report(db_session, await member(db_session), "alice")
    await purge_pending_deletions(db_session)

    (row,) = await _reports(db_session)
    assert _report_author({"reporter_name": row.reporter_name, "anonymous": row.anonymous}, "Admin") == ""


async def test_the_blacklist_no_longer_lists_them(db_session):
    await gdpr_on(db_session)
    alice = await member(db_session)
    bob = await member(db_session, "bob", guid="EMBY-BOB", overdue=False)
    await _blocked(db_session, 1, alice, bob)
    await _blocked(db_session, 2, alice)
    await _blocked(db_session, 3)
    expected_bob = {"user_id": bob.id, "display_name": "bob"}

    await purge_pending_deletions(db_session)

    assert await _requesters(db_session) == [[expected_bob], [], None]


async def test_a_local_account_loses_its_name_too(db_session):
    await gdpr_on(db_session)
    dave = await member(db_session, "dave", guid=None, source=SOURCE_LOCAL)
    await _report(db_session, dave, "dave")
    await _blocked(db_session, 1, dave)

    await purge_pending_deletions(db_session)

    assert (await _reports(db_session))[0].reporter_name is None
    assert await _requesters(db_session) == [[]]


async def test_a_failed_deletion_leaves_the_names_in_place(db_session):
    await gdpr_on(db_session)
    alice = await member(db_session)
    await _report(db_session, alice, "alice")
    await _blocked(db_session, 1, alice)
    expected = [[{"user_id": alice.id, "display_name": "alice"}]]

    with patch.object(db_session, "delete", new=AsyncMock(side_effect=RuntimeError("boom"))), \
         pytest.raises(RuntimeError):
        await purge_pending_deletions(db_session)
    await db_session.rollback()

    (row,) = await _reports(db_session)
    assert (row.reporter_name, row.anonymous) == ("alice", False)
    assert await _requesters(db_session) == expected
