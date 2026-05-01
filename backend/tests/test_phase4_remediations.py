import pytest
from sqlalchemy import func, select

from core.security import hash_password
from models.portal.request import MediaRequest, RequestVote
from models.user import User
from services.backup.restore import restore_json_backup
from services.portal import requests as req_svc
from services.settings import get_user_preferences


async def _create_user(db_session, username: str = "phase4-user") -> User:
    user = User(
        username=username,
        hashed_password=hash_password("Phase4Password123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_create_request_no_longer_creates_vote_rows(db_session):
    user = await _create_user(db_session)

    result = await req_svc.create_request(
        db_session,
        user.id,
        {
            "tmdb_id": 4242,
            "media_type": "movie",
            "title": "Unique Request",
        },
    )

    assert result["success"] is True

    req = await db_session.get(MediaRequest, result["id"])
    assert req is not None
    assert req.vote_count == 0

    votes = await db_session.execute(select(func.count(RequestVote.id)))
    assert votes.scalar_one() == 0


@pytest.mark.asyncio
async def test_create_request_rejects_existing_available_request(db_session):
    user = await _create_user(db_session, "phase4-available")

    existing = MediaRequest(
        user_id=user.id,
        tmdb_id=3131,
        media_type="movie",
        title="Already Landed",
        status="available",
    )
    db_session.add(existing)
    await db_session.commit()

    result = await req_svc.create_request(
        db_session,
        user.id,
        {
            "tmdb_id": 3131,
            "media_type": "movie",
            "title": "Already Landed",
        },
    )

    assert result == {"error": "already_requested"}


@pytest.mark.asyncio
async def test_vote_requests_are_explicitly_disabled(db_session):
    result = await req_svc.vote_request(db_session, request_id=1, user_id=1)
    assert result == {"error": "votes_disabled"}


@pytest.mark.asyncio
async def test_restore_preferences_rolls_back_component_on_error(db_session):
    user = await _create_user(db_session, "phase4-restore")
    user_id = user.id

    result = await restore_json_backup(
        db_session,
        [
            {
                "user_id": user_id,
                "preferences": {"theme": "dark"},
                "dashboard_layout": {"hidden": []},
            },
            {
                "preferences": {"theme": "light"},
            },
        ],
        components={"preferences": True},
    )

    assert result["preferences"].startswith("error:")
    row = await get_user_preferences(db_session, user_id)
    assert row is None
