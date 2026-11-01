"""What the personal data export holds of the sign-in log and the profile, and that
its README stays true: every table bound to an account is exported or owned up to."""
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from models.base import Base
from models.portal.profile import UserProfile
from models.security import SecurityAttempt
from services.portal.admin_users_lifecycle import soft_delete_user
from services.portal.gdpr import _collect_full_user_data
from services.settings import set_setting
from tests._portal_profile_helpers import PORTAL_COOKIE, portal_token
from tests._signin_media_server_helpers import ACCEPTED, add_member, media_server, sign_in

PROFILE_LEFT_OUT = {"admin_notes", "tags", "deleted_at", "deleted_by_user_id"}
TABLES_EXPORTED = {
    "user_profiles", "user_preferences", "user_lists", "user_list_items", "user_ratings",
    "user_achievements", "release_reminders", "chat_messages", "media_requests", "watch_party_participants",
}
TABLES_NOT_EXPORTED_YET = {
    "tickets", "ticket_replies", "feedback_reports", "chat_reports", "xp_ledger", "seasonal_progress",
    "request_quotas", "mk_notifications", "mk_events", "mk_event_invitations", "mk_event_messages",
    "watch_parties", "user_list_contributors", "user_list_history", "user_rating_likes", "news_reads",
    "seen_alerts", "chat_mutes",
}
# Only ever point at the admin who acted, never at the person the row is about.
TABLES_NAMING_THE_ADMIN = {"security_blocks", "news", "featured_heroes", "seasonal_events", "request_blacklist"}


async def _profile(db_session, user) -> UserProfile:
    return (await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )).scalar_one()


async def _log(db_session, name, *, success=1, scope="portal", ip="198.51.100.1", at=None) -> None:
    db_session.add(SecurityAttempt(
        ip=ip, username=name, scope=scope, success=success, user_agent="TestBrowser/1.2.3",
        created_at=at or datetime.now(timezone.utc) + timedelta(minutes=1),
    ))
    await db_session.commit()


async def _exported_sign_ins(db_session, user) -> list[dict]:
    out = await _collect_full_user_data(db_session, user, await _profile(db_session, user))
    return out["security_attempts"]


@pytest.mark.asyncio
async def test_only_successful_sign_ins_are_exported(db_session):
    user = await add_member(db_session)
    await _log(db_session, "member-a", ip="198.51.100.1")
    await _log(db_session, "member-a", ip="198.51.100.2", success=0)

    rows = await _exported_sign_ins(db_session, user)

    assert [row["ip"] for row in rows] == ["198.51.100.1"]
    assert set(rows[0]) == {"id", "scope", "ip", "user_agent", "created_at"}
    assert rows[0]["user_agent"] == "TestBrowser/1.2.3"
    assert datetime.fromisoformat(rows[0]["created_at"])


@pytest.mark.asyncio
async def test_another_name_stays_out(db_session):
    user = await add_member(db_session)
    await _log(db_session, "member-b")

    assert await _exported_sign_ins(db_session, user) == []


@pytest.mark.parametrize("account, logged", [
    ("member-a", ["member-a", "Member-A", "MEMBER-A"]),
    ("Member-A", ["member-a", "Member-A", "MEMBER-A"]),
    # The test database lower-cases only plain letters, as some PostgreSQL setups do.
    ("Émile", ["émile", "Émile", "ÉMILE"]),
])
@pytest.mark.asyncio
async def test_older_rows_kept_the_letter_case_typed(db_session, account, logged):
    user = await add_member(db_session, account)
    for name in logged:
        await _log(db_session, name)

    assert len(await _exported_sign_ins(db_session, user)) == 3


@pytest.mark.asyncio
async def test_a_password_change_shows_with_its_scope(db_session):
    user = await add_member(db_session)
    await _log(db_session, "member-a", scope="admin_password")

    assert [row["scope"] for row in await _exported_sign_ins(db_session, user)] == ["admin_password"]


@pytest.mark.asyncio
async def test_a_past_holder_of_the_name_stays_out(db_session):
    """Purged accounts leave the log behind, and their name can be taken again."""
    await _log(db_session, "member-a", ip="198.51.100.9", at=datetime.now(timezone.utc) - timedelta(days=30))
    user = await add_member(db_session)
    await _log(db_session, "member-a", ip="198.51.100.1")

    assert [row["ip"] for row in await _exported_sign_ins(db_session, user)] == ["198.51.100.1"]


async def _export_of(client, db_session, name) -> zipfile.ZipFile:
    await set_setting(db_session, "gdpr.enabled", "true")
    client.cookies.set(PORTAL_COOKIE, portal_token(name))
    resp = await client.get("/api/portal/me/export")
    assert resp.status_code == 200, resp.text
    return zipfile.ZipFile(io.BytesIO(resp.content))


@pytest.mark.asyncio
async def test_a_real_sign_in_reaches_the_export_but_not_a_wrong_password(client, db_session):
    await add_member(db_session)
    with media_server(httpx.Response(401)):
        assert (await sign_in(client, "MEMBER-A")).status_code == 401
    with media_server(ACCEPTED):
        assert (await sign_in(client, " MEMBER-A ", "any")).status_code == 200

    with await _export_of(client, db_session, "member-a") as archive:
        rows = json.loads(archive.read("security_attempts.json"))

    assert [row["scope"] for row in rows] == ["portal"]


@pytest.mark.asyncio
async def test_a_sign_in_under_another_server_name_is_not_found_as_the_readme_says(client, db_session):
    await add_member(db_session, "member-a", emby_id="emby-id-a")
    with media_server(ACCEPTED):
        assert (await sign_in(client, "new-name", "any")).json()["username"] == "member-a"

    with await _export_of(client, db_session, "member-a") as archive:
        rows = json.loads(archive.read("security_attempts.json"))
        readme = archive.read("README.txt").decode()

    assert rows == []
    assert "sign-ins made under another name" in readme


@pytest.mark.asyncio
async def test_the_readme_lists_the_sign_ins_and_owns_up_to_what_is_missing(client, db_session):
    await add_member(db_session)

    with await _export_of(client, db_session, "member-a") as archive:
        readme = archive.read("README.txt").decode()

    assert "  - security_attempts.json" in readme
    assert "failed sign-ins" in readme
    assert "Not in this archive yet" in readme
    assert "every row" not in readme


@pytest.mark.asyncio
async def test_a_deleted_account_cannot_ask_for_an_export(client, db_session):
    """Why the profile's deletion markers are left out: they could only ever be empty."""
    user = await add_member(db_session)
    await set_setting(db_session, "gdpr.enabled", "true")
    client.cookies.set(PORTAL_COOKIE, portal_token("member-a"))
    await soft_delete_user(db_session, await _profile(db_session, user), user, admin_user_id=None)

    assert (await client.get("/api/portal/me/export")).status_code == 401


@pytest.mark.asyncio
async def test_every_profile_column_is_exported_or_left_out_on_purpose(db_session):
    """A new column must be decided on here, not silently missed or leaked."""
    user = await add_member(db_session)
    out = await _collect_full_user_data(db_session, user, await _profile(db_session, user))

    assert set(out["user_profile"]) == set(UserProfile.__table__.columns.keys()) - PROFILE_LEFT_OUT


@pytest.mark.asyncio
async def test_the_profile_dates_and_rights_read_as_stored(db_session):
    until = datetime(2030, 1, 2, 3, 4, tzinfo=timezone.utc)
    user = await add_member(db_session, chat_muted_until=until, can_chat=False)

    out = await _collect_full_user_data(db_session, user, await _profile(db_session, user))

    assert out["user_profile"]["chat_muted_until"].startswith("2030-01-02T03:04")
    assert out["user_profile"]["can_chat"] is False
    assert out["user_profile"]["can_portal"] is True


def test_every_table_bound_to_an_account_is_exported_or_owned_up_to():
    """A new table must be decided on here, then added to the export or to the README."""
    bound = {
        table.name for table in Base.metadata.tables.values()
        if any(fk.target_fullname == "users.id" for fk in table.foreign_keys)
    }

    assert bound == TABLES_EXPORTED | TABLES_NOT_EXPORTED_YET | TABLES_NAMING_THE_ADMIN
