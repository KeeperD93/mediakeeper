import pytest

from core.security import hash_password
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.request import MediaRequest
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


_LANDED = {"tmdb_id": 3131, "media_type": "movie", "title": "Already Landed"}


@pytest.mark.asyncio
async def test_create_request_rejects_a_landed_title(db_session):
    """A title Emby holds is refused."""
    user = await _create_user(db_session, "phase4-available")
    db_session.add(EmbyTmdbIndex(emby_item_id="EMBY-3131", tmdb_id=3131, media_type="movie"))
    await db_session.commit()

    assert await req_svc.create_request(db_session, user.id, _LANDED) == {"error": "already_available"}


@pytest.mark.asyncio
async def test_served_request_alone_no_longer_blocks(db_session):
    """The title may have left Emby since it was served: it can be asked again."""
    user = await _create_user(db_session, "phase4-served")
    db_session.add(MediaRequest(user_id=user.id, status="available", **_LANDED))
    await db_session.commit()

    assert (await req_svc.create_request(db_session, user.id, _LANDED))["success"] is True


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
