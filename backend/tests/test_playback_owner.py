"""A player's plays are found by their Emby account, never by a name anyone can choose."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackPauseEvent, PlaybackSession
from models.portal.achievement import UserAchievement
from services.portal.achievements import check_all_achievements, seed_achievements
from services.portal.achievements_seasonal import _compute_seasonal_years
from services.portal.achievements_utils import (
    _build_pause_user_filter,
    _build_playback_user_filter,
)
from services.portal.personal_utils import _count_total_plays, _playback_user_filter
from services.portal.profiles import update_profile
from services.portal.user_import import ensure_user_for_emby_session
from services.portal.zone_correction._plan import _player_plays
from tests._portal_profile_helpers import make_portal_user

CHRISTMAS = datetime(2025, 12, 25, 20, tzinfo=UTC)
NO_EXCLUSION = SimpleNamespace(excl_filters=[])


def _play(db, emby_id: str, name: str, key: str, started: datetime = CHRISTMAS) -> None:
    db.add(PlaybackSession(
        session_key=key, user_id=emby_id, user_name=name, item_id=f"item-{key}",
        item_name="Test Movie", item_type="Movie", library_name="Movies",
        started_at=started, last_seen_at=started + timedelta(hours=2),
        ended_at=started + timedelta(hours=2), is_active=False, measured=True,
        watched_seconds=7200, exclusive_seconds=7200,
    ))


def _pause(db, emby_id: str, name: str, key: str) -> None:
    db.add(PlaybackPauseEvent(
        session_key=key, user_id=emby_id, user_name=name, item_id=f"item-{key}",
        item_name="Test Movie", item_type="Movie", pause_started_at=CHRISTMAS,
    ))


async def _keys(db, clause, model=PlaybackSession) -> set[str]:
    return set((await db.execute(select(model.session_key).where(clause))).scalars())


async def _movies_counted(db, user_id: int) -> int:
    return (await db.execute(select(UserAchievement.progress).where(
        UserAchievement.user_id == user_id, UserAchievement.achievement_id == "movie_buff_1",
    ))).scalar_one()


async def _alice_takes_the_pseudo_of_bobs_login(db):
    """Bob now goes by another pseudo; his Emby name stays the one Alice picks."""
    await make_portal_user(db, username="Bob", display_name="Bob le Grand", emby_user_id="emby-bob")
    alice, profile = await make_portal_user(
        db, username="Alice", display_name="Alice", emby_user_id="emby-alice", must_set=True,
    )
    _play(db, "emby-bob", "Bob", "bob-1")
    _play(db, "emby-bob", "Bob", "bob-2", CHRISTMAS + timedelta(days=1))
    _play(db, "emby-alice", "Alice", "alice-1", datetime(2026, 3, 1, 20, tzinfo=UTC))
    _pause(db, "emby-bob", "Bob", "bob-1")
    _pause(db, "emby-alice", "Alice", "alice-1")
    await db.commit()
    profile = await update_profile(db, profile, {"display_name": "Bob"})
    assert profile.display_name == "Bob"
    return alice, profile


@pytest.mark.asyncio
async def test_a_pseudo_equal_to_an_emby_name_takes_no_play(db_session):
    alice, profile = await _alice_takes_the_pseudo_of_bobs_login(db_session)
    assert await _count_total_plays(db_session, alice, profile) == 1
    assert await _keys(db_session, _playback_user_filter(alice, profile)) == {"alice-1"}


@pytest.mark.asyncio
async def test_every_reader_ignores_the_pseudo(db_session):
    alice, _ = await _alice_takes_the_pseudo_of_bobs_login(db_session)
    played = await _build_playback_user_filter(db_session, alice.id)
    paused = await _build_pause_user_filter(db_session, alice.id)
    plays = await _player_plays(db_session, NO_EXCLUSION, alice.id)

    assert await _keys(db_session, played) == {"alice-1"}
    assert await _keys(db_session, paused, PlaybackPauseEvent) == {"alice-1"}
    assert [row.session_key for row in plays.rows] == ["alice-1"]
    assert plays.emby_ids == ["emby-alice"]
    assert (await _compute_seasonal_years(db_session, alice.id))["secret_christmas"] == []


@pytest.mark.asyncio
async def test_trophies_do_not_count_the_plays_of_another_player(db_session):
    await seed_achievements(db_session)
    alice, profile = await make_portal_user(
        db_session, username="Alice", emby_user_id="emby-alice", must_set=True,
    )
    await make_portal_user(db_session, username="Bob", display_name="Bob le Grand", emby_user_id="emby-bob")
    _play(db_session, "emby-alice", "Alice", "alice-1")
    for day in range(3):
        _play(db_session, "emby-bob", "Bob", f"bob-{day}", CHRISTMAS + timedelta(days=day + 1))
    await db_session.commit()

    await update_profile(db_session, profile, {"display_name": "Bob"})
    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _movies_counted(db_session, alice.id) == 1


@pytest.mark.asyncio
async def test_a_player_renamed_in_emby_keeps_all_their_plays(db_session):
    await seed_achievements(db_session)
    bob, profile = await make_portal_user(db_session, username="Bob", emby_user_id="emby-bob")
    for day in range(2):
        _play(db_session, "emby-bob", "Bob", f"old-{day}", CHRISTMAS + timedelta(days=day))
    for day in range(3):
        _play(db_session, "emby-bob", "Robert", f"new-{day}", CHRISTMAS + timedelta(days=day + 10))
    await db_session.commit()

    assert await _count_total_plays(db_session, bob, profile) == 5
    await check_all_achievements(db_session, bob.id, bob.username)
    assert await _movies_counted(db_session, bob.id) == 5


@pytest.mark.asyncio
async def test_the_correction_tool_reads_the_same_plays_as_the_pass(db_session):
    bob, _ = await make_portal_user(db_session, username="Bob", emby_user_id="emby-bob")
    await make_portal_user(db_session, username="Carol", emby_user_id="emby-carol")
    _play(db_session, "emby-bob", "Bob", "own")
    _play(db_session, "emby-bob", "Robert", "renamed", CHRISTMAS + timedelta(days=1))
    _play(db_session, "emby-carol", "Bob", "same-name-other-player", CHRISTMAS + timedelta(days=2))
    await db_session.commit()

    plays = await _player_plays(db_session, NO_EXCLUSION, bob.id)
    pass_keys = await _keys(db_session, await _build_playback_user_filter(db_session, bob.id))
    assert {row.session_key for row in plays.rows} == pass_keys == {"own", "renamed"}


@pytest.mark.asyncio
async def test_the_login_claims_only_an_emby_account_linked_to_nobody(db_session):
    # Emby reinstalled: same name, new ids, and the profile still holds the old one.
    bob, profile = await make_portal_user(db_session, username="Bob", emby_user_id="emby-old")
    await make_portal_user(db_session, username="Carol", emby_user_id="emby-carol")
    _play(db_session, "emby-old", "Bob", "before-reinstall")
    _play(db_session, "emby-new", "Bob", "after-reinstall", CHRISTMAS + timedelta(days=1))
    _play(db_session, "emby-carol", "Bob", "carol-renamed-bob", CHRISTMAS + timedelta(days=2))
    await db_session.commit()

    assert await _keys(db_session, _playback_user_filter(bob, profile)) == {
        "before-reinstall", "after-reinstall",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("emby_name", ["bob", "BOB"])
async def test_the_login_claim_ignores_case_like_the_collector(db_session, emby_name):
    bob, profile = await make_portal_user(db_session, username="Bob", emby_user_id="emby-old")
    _play(db_session, "emby-new", emby_name, "after-reinstall")
    await db_session.commit()

    resolved = await ensure_user_for_emby_session(
        db_session, emby_username=emby_name, emby_user_id="emby-new",
    )
    assert resolved.id == bob.id
    assert await _keys(db_session, _playback_user_filter(bob, profile)) == {"after-reinstall"}


@pytest.mark.asyncio
async def test_an_unlinked_account_goes_by_its_login_only(db_session):
    local, profile = await make_portal_user(
        db_session, username="Dana", display_name="Bob", emby_user_id=None,
    )
    await make_portal_user(db_session, username="Bob", emby_user_id="emby-bob")
    _play(db_session, "emby-bob", "Bob", "bobs")
    _play(db_session, "emby-bob", "Dana", "bob-renamed-dana", CHRISTMAS + timedelta(days=1))
    _play(db_session, "emby-nobody", "Dana", "unlinked-account", CHRISTMAS + timedelta(days=2))
    await db_session.commit()

    assert await _keys(db_session, _playback_user_filter(local, profile)) == {"unlinked-account"}


@pytest.mark.asyncio
async def test_without_an_account_no_row_matches(db_session):
    _play(db_session, "emby-bob", "Bob", "bobs")
    await db_session.commit()

    assert await _build_playback_user_filter(db_session, 99999) is None
    assert await _build_pause_user_filter(db_session, 99999) is None
    assert await _keys(db_session, _playback_user_filter(None, None)) == set()
