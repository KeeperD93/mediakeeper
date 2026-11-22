"""The watch XP recalculation endpoints: admin only."""
import pytest

from tests._watch_xp_helpers import T, account, watched
from tests._watch_xp_recalc_helpers import sign_in_as

SIMULATE = "/api/portal/admin/debug/watch-xp/simulate"


@pytest.mark.asyncio
async def test_a_viewer_cannot_simulate(client, db_session):
    await sign_in_as(client, db_session, "bob", "viewer")

    assert (await client.get(SIMULATE)).status_code == 403


@pytest.mark.asyncio
async def test_an_admin_gets_the_summary_of_the_plan(client, db_session):
    await sign_in_as(client, db_session, "admin", "admin")
    await account(db_session, "alice")
    await watched(db_session, at=T)

    resp = await client.get(SIMULATE)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["players"], body["players_changed"], body["watch_xp_after"]) == (1, 1, 40)
    assert len(body["plan"]) == 16 and body["rows"][0]["name"] == "Alice"
