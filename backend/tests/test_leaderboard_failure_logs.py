"""A ranking that fails stays empty on screen, and must reach the normal logs."""
import logging

import pytest

from services.portal import profile_stats_ranking
from services.portal._leaderboard_helpers import empty_payload
from services.portal.profile_stats_ranking import (
    compute_leaderboard_only,
    compute_ranking,
)
from tests._portal_profile_helpers import make_portal_user

LOGGER = "mediakeeper.portal.profile_stats"


@pytest.fixture
def broken_ranking(monkeypatch):
    async def fail(db):
        raise RuntimeError("database down")

    monkeypatch.setattr(profile_stats_ranking, "excluded_from_leaderboard", fail)


def _logged(caplog) -> list[tuple[str, str]]:
    return [(r.levelname, r.getMessage()) for r in caplog.records if r.name == LOGGER]


@pytest.mark.asyncio
async def test_a_failed_leaderboard_is_logged_and_stays_empty(
    db_session, broken_ranking, caplog
):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        payload = await compute_leaderboard_only(db_session, lang="en")

    assert payload == empty_payload("en")
    assert _logged(caplog) == [("ERROR", "[LEADERBOARD-ONLY] failed: database down")]


@pytest.mark.asyncio
async def test_a_failed_profile_ranking_is_logged_and_stays_empty(
    db_session, broken_ranking, caplog
):
    alice, _ = await make_portal_user(db_session, username="alice")

    with caplog.at_level(logging.INFO, logger=LOGGER):
        ranking = await compute_ranking(db_session, alice)

    assert ranking == {
        "position": 0,
        "total": 0,
        "percentile": 0,
        "movement": 0,
        "leaderboard": [],
    }
    assert _logged(caplog) == [("ERROR", "[PROFILE] ranking failed: database down")]
