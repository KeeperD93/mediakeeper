"""A refused request gets a plain 422 that never repeats what it sent: the value may
be a password, and one that cannot be encoded used to turn the refusal into a 500
and a logged trace, ahead of any rate limit."""
from __future__ import annotations

import pytest

JSON_HEADERS = {"Content-Type": "application/json"}


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/api/auth/login", "/api/auth/portal-login"])
@pytest.mark.parametrize(
    "body",
    [
        pytest.param(rb'{"username":"a\ud800","password":"x"}', id="lone-surrogate-in-username"),
        pytest.param(rb'{"username":"alice","password":"a\ud800"}', id="lone-surrogate-in-password"),
        pytest.param(rb'{"username":"alice","password":"x","a\ud800":"y"}', id="lone-surrogate-in-field-name"),
        pytest.param(b'{"username":NaN,"password":"x"}', id="not-a-number"),
    ],
)
async def test_a_value_that_cannot_be_encoded_is_a_plain_refusal(client, caplog, route, body):
    resp = await client.post(route, content=body, headers=JSON_HEADERS)

    assert resp.status_code == 422
    assert resp.json()["detail"]
    assert not [record for record in caplog.records if record.exc_info]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"username": "alice", "password": "Test-Secret-" * 50}, id="too-long"),
        pytest.param({"username": "alice", "password": "x", "unknown": "Test-Secret-"}, id="unknown-field"),
    ],
)
async def test_a_refusal_never_repeats_what_was_sent(client, payload):
    resp = await client.post("/api/auth/login", json=payload)

    assert resp.status_code == 422
    assert "Test-Secret-" not in resp.text
    assert all(error.keys() == {"type", "loc", "msg"} for error in resp.json()["detail"])


@pytest.mark.asyncio
async def test_broken_json_keeps_its_refusal_code(client):
    resp = await client.post("/api/auth/login", content=b'{"username":', headers=JSON_HEADERS)

    assert resp.status_code == 422
    assert resp.json()["detail"][0]["type"] == "json_invalid"
