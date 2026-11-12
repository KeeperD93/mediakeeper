"""Stats exclusions endpoints: each write answers with the whole list, so the
Tools tab shows it without fetching again."""
import json

import pytest

from core.security import create_access_token
from services.settings import set_setting


def _sign_in(client, user):
    client.cookies.set("mk_token", create_access_token({"sub": user.username, "scope": "admin"}))


def _remove(client, mode, value):
    return client.request("DELETE", "/api/stats/exclusions", json={"mode": mode, "value": value})


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
async def test_delete_removes_the_named_entry_after_the_list_changed(client, admin_user):
    _sign_in(client, admin_user)
    for value in ("First title", "Second title", "Third title"):
        await client.post("/api/stats/exclusions", json={"mode": "exact", "value": value})
    # Another tab removes the first entry: this one still shows "Second title" in second place.
    await _remove(client, "exact", "First title")

    r = await _remove(client, "exact", "Second title")
    assert r.status_code == 200, r.text
    left = [{"mode": "exact", "value": "Third title"}]
    assert r.json() == left
    # Already gone: nothing else is removed and the current list comes back.
    assert (await _remove(client, "exact", "Second title")).json() == left


@pytest.mark.asyncio
async def test_delete_keeps_the_same_title_under_the_other_mode(client, admin_user):
    _sign_in(client, admin_user)
    for mode in ("exact", "contains"):
        await client.post("/api/stats/exclusions", json={"mode": mode, "value": "Trailer"})

    r = await _remove(client, "contains", "Trailer")
    assert r.json() == [{"mode": "exact", "value": "Trailer"}]


@pytest.mark.asyncio
async def test_delete_removes_an_entry_saved_before_values_were_trimmed(
    client, admin_user, db_session,
):
    _sign_in(client, admin_user)
    await set_setting(
        db_session, "stats.exclusions", json.dumps([{"mode": "exact", "value": " Old title "}]),
    )

    assert (await _remove(client, "exact", " Old title ")).json() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "DELETE"])
@pytest.mark.parametrize("body", [{"mode": "exact", "value": "   "}, {"mode": "regex", "value": "Sample"}])
async def test_invalid_exclusion_is_refused(client, admin_user, method, body):
    _sign_in(client, admin_user)
    assert (await client.request(method, "/api/stats/exclusions", json=body)).status_code == 422
