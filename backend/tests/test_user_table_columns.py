"""Per-user resizable table column widths — GET/PUT /api/auth/table-columns."""
import pytest


@pytest.mark.asyncio
async def test_table_columns_empty_by_default(authed_client):
    r = await authed_client.get("/api/auth/table-columns")
    assert r.status_code == 200
    assert r.json() == {}


@pytest.mark.asyncio
async def test_table_columns_roundtrip_and_merge(authed_client):
    r = await authed_client.put(
        "/api/auth/table-columns",
        json={"table": "stats.activity", "widths": [40, 120, 200]},
    )
    assert r.status_code == 200

    r = await authed_client.put(
        "/api/auth/table-columns",
        json={"table": "stats.users", "widths": [60, 300]},
    )
    assert r.status_code == 200

    # Both tables persist under their own key; neither overwrites the other.
    r = await authed_client.get("/api/auth/table-columns")
    assert r.json() == {"stats.activity": [40, 120, 200], "stats.users": [60, 300]}


@pytest.mark.asyncio
async def test_table_columns_update_overwrites_same_table(authed_client):
    await authed_client.put(
        "/api/auth/table-columns", json={"table": "t", "widths": [10, 20]},
    )
    await authed_client.put(
        "/api/auth/table-columns", json={"table": "t", "widths": [30, 40, 50]},
    )
    r = await authed_client.get("/api/auth/table-columns")
    assert r.json() == {"t": [30, 40, 50]}


@pytest.mark.asyncio
async def test_table_columns_rejects_unknown_field(authed_client):
    r = await authed_client.put(
        "/api/auth/table-columns",
        json={"table": "t", "widths": [10], "bogus": 1},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_table_columns_rejects_out_of_range_width(authed_client):
    r = await authed_client.put(
        "/api/auth/table-columns",
        json={"table": "t", "widths": [10, 99999]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_table_columns_rejects_boolean_width(authed_client):
    # A JSON ``true`` must not slip through as width 1 (StrictInt rejects bools).
    r = await authed_client.put(
        "/api/auth/table-columns",
        json={"table": "t", "widths": [True, 50]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_table_columns_eviction_keeps_just_saved_table(authed_client):
    """At the cap, re-saving an old table moves it to the most-recent slot so it
    survives when a new table pushes the map over the limit."""
    from api.auth.profile import MAX_TABLE_PREFS

    for i in range(MAX_TABLE_PREFS):
        r = await authed_client.put(
            "/api/auth/table-columns", json={"table": f"t{i}", "widths": [10]},
        )
        assert r.status_code == 200
    # Re-save the oldest table, then push the map over the cap with a new one.
    await authed_client.put("/api/auth/table-columns", json={"table": "t0", "widths": [20]})
    await authed_client.put("/api/auth/table-columns", json={"table": "tNew", "widths": [30]})

    body = (await authed_client.get("/api/auth/table-columns")).json()
    assert len(body) == MAX_TABLE_PREFS
    assert body["t0"] == [20]  # re-saved -> moved to recent -> kept
    assert "tNew" in body
    assert "t1" not in body  # now the oldest -> evicted
