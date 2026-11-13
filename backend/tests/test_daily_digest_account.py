"""Viewer blocks of the daily digest: the public name, the expiry warning,
yesterday's XP and the avatar frame of the ranking rows."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from constants.daily_digest import EXPIRY_WARNING_DAYS
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal import daily_digest_account as account
from services.portal import daily_digest_sources as sources
from services.portal._leaderboard_helpers import build_entry
from services.portal._pseudo_words import generate_pseudo
from tests._portal_profile_helpers import make_portal_user

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)


def _profile(**fields) -> UserProfile:
    values = {
        "user_id": 12345, "display_name": "Alice", "display_name_must_set": False,
        "role": "viewer", "level": 12,
    }
    return UserProfile(**(values | fields))


def test_me_shows_the_chosen_name_with_its_frame_and_tier():
    me = account.me(_profile(avatar_effect="watching", avatar_url="/api/emby/user-image/1"), "fr")
    assert me == {
        "display_name": "Alice",
        "avatar_url": "/api/emby/user-image/1",
        "avatar_effect": "watching",
        "tier": "gold",
    }


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_me_never_shows_the_login_of_an_unconfirmed_account(lang):
    me = account.me(_profile(display_name="alice_login", display_name_must_set=True), lang)
    assert me["display_name"] == generate_pseudo(12345, lang)


def test_me_names_the_administrator_by_the_role_label():
    assert account.me(_profile(role="admin"), "en")["display_name"] == "Administrator"


def test_no_expiry_without_an_end_date():
    assert account.expiry(_profile(), now=NOW, zone=UTC) is None


@pytest.mark.parametrize(
    ("days", "shown"), [(EXPIRY_WARNING_DAYS, True), (EXPIRY_WARNING_DAYS + 1, False)],
)
def test_the_expiry_warning_starts_30_days_before_the_end(days, shown):
    end = NOW + timedelta(days=days)
    block = account.expiry(_profile(access_end_date=end), now=NOW, zone=UTC)
    assert block == ({"ends_at": end.isoformat(), "days_left": days} if shown else None)


@pytest.mark.parametrize("end", [NOW - timedelta(minutes=1), NOW])
def test_an_ended_access_has_no_warning(end):
    assert account.expiry(_profile(access_end_date=end), now=NOW, zone=UTC) is None


def test_the_days_left_follow_the_calendar_of_the_instance():
    # 00:10 on Wednesday in Paris, still Tuesday in UTC; the access ends at 11:00 that Wednesday.
    now = datetime(2026, 11, 3, 23, 10, tzinfo=UTC)
    profile = _profile(access_end_date=datetime(2026, 11, 4, 10, 0, tzinfo=UTC))
    assert account.expiry(profile, now=now, zone=PARIS)["days_left"] == 0
    assert account.expiry(profile, now=now, zone=UTC)["days_left"] == 1


def test_an_end_date_without_offset_is_read_as_utc():
    """SQLite drops the offset of the stored date."""
    end = NOW + timedelta(days=2)
    block = account.expiry(_profile(access_end_date=end.replace(tzinfo=None)), now=NOW, zone=PARIS)
    assert block == {"ends_at": end.isoformat(), "days_left": 2}


@pytest.mark.asyncio
async def test_the_xp_of_yesterday_follows_the_days_of_the_instance(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    # Wednesday 11:00 in Paris: yesterday ran from 23:00 UTC on Monday to 23:00 UTC on Tuesday.
    now = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    rows = [
        (alice, datetime(2026, 11, 2, 22, 59, tzinfo=UTC), 100),  # Monday 23:59 in Paris
        (alice, datetime(2026, 11, 2, 23, 0, tzinfo=UTC), 10),  # Tuesday 00:00
        (alice, datetime(2026, 11, 3, 22, 59, tzinfo=UTC), 5),  # Tuesday 23:59
        (alice, datetime(2026, 11, 3, 23, 0, tzinfo=UTC), 1000),  # Wednesday 00:00
        (bob, datetime(2026, 11, 3, 12, 0, tzinfo=UTC), 50),
    ]
    db_session.add_all(
        XpLedger(user_id=user.id, action="test_action", reference=f"ref-{idx}", xp=xp, created_at=at)
        for idx, (user, at, xp) in enumerate(rows)
    )
    await db_session.commit()

    assert await account.xp_yesterday(db_session, alice.id, now=now, zone=PARIS) == 15
    assert await account.xp_yesterday(db_session, alice.id, now=now, zone=UTC) == 1005
    assert await account.xp_yesterday(db_session, 99999, now=now, zone=PARIS) == 0


def test_a_ranking_row_carries_the_avatar_frame():
    row = SimpleNamespace(user_id=12345, total_xp=300)
    kwargs = {
        "prev_rank_by_user": None, "trophies_by_user": {}, "viewer_user_id": None, "lang": "fr",
    }
    framed = {12345: _profile(avatar_effect="watching")}
    assert build_entry(0, row, prof_by_id=framed, **kwargs)["avatar_effect"] == "watching"
    assert build_entry(0, row, prof_by_id={}, **kwargs)["avatar_effect"] is None


@pytest.mark.asyncio
async def test_the_digest_top3_keeps_the_avatar_frame(db_session):
    rows = [
        {"rank": 1, "avatar_effect": "watching", "is_current_user": True},
        {"rank": 2, "is_current_user": False},
    ]
    ranking = {"position": 1, "total": 2, "movement": 0, "leaderboard": rows}
    with patch.object(sources, "compute_ranking", AsyncMock(return_value=ranking)):
        snapshot = await sources.ranking_snapshot(db_session, User(username="alice"))
    assert [row["avatar_effect"] for row in snapshot["top3"]] == ["watching", None]
