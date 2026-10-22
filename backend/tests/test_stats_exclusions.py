"""Stats exclusions endpoints: each write answers with the whole list, so the
Tools tab shows it without fetching again."""
import pytest

from core.security import create_access_token


def _sign_in(client, user):
    client.cookies.set("mk_token", create_access_token({"sub": user.username, "scope": "admin"}))


@pytest.mark.asyncio
async def test_add_answers_with_the_whole_list_and_skips_a_duplicate(client, admin_user):
    _sign_in(client, admin_user)
    r = await client.post("/api/stats/exclusions", json={"mode": "exact", "value": "  Sample title  "})
    assert r.status_code == 200, r.text
    assert r.json() == [{"mode": "exact", "value": "Sample title"}]

    r = await client.post("/api/stats/exclusions", json={"mode": "contains", "value": "Trailer"})
    both = [{"mode": "exact", "value": "Sample title"}, {"mode": "contains", "value": "Trailer"}]
    assert r.json() == both

    r = await client.post("/api/stats/exclusions", json={"mode": "exact", "value": "Sample title"})
    assert r.json() == both
    assert (await client.get("/api/stats/exclusions")).json() == both


@pytest.mark.asyncio
async def test_delete_by_position_answers_with_the_list(client, admin_user):
    _sign_in(client, admin_user)
    for value in ("First title", "Second title"):
        await client.post("/api/stats/exclusions", json={"mode": "exact", "value": value})

    r = await client.delete("/api/stats/exclusions/0")
    assert r.status_code == 200, r.text
    left = [{"mode": "exact", "value": "Second title"}]
    assert r.json() == left
    # Out of range: nothing is removed and the same list comes back.
    assert (await client.delete("/api/stats/exclusions/5")).json() == left


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"mode": "exact", "value": "   "}, {"mode": "regex", "value": "Sample"}])
async def test_invalid_exclusion_is_refused(client, admin_user, body):
    _sign_in(client, admin_user)
    assert (await client.post("/api/stats/exclusions", json=body)).status_code == 422
