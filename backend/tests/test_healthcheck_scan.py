from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from models.healthcheck import HealthCheckResult
from services.healthcheck import scan as health_scan


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_run_healthcheck_keeps_previous_results_when_scan_fails(monkeypatch, db_session):
    db_session.add(HealthCheckResult(
        item_id="existing",
        item_name="Existing",
        item_type="Movie",
        issues="[]",
        severity="info",
    ))
    await db_session.commit()

    async def fake_load_config(_db):
        return {}

    async def fake_get_source(_db):
        return {"source": "emby", "url": "http://emby.test", "api_key": "token"}

    class FakeClient:
        async def get(self, url, params=None, headers=None, timeout=None):
            if params and params.get("Limit") == 0:
                return _FakeResponse(200, {"TotalRecordCount": 1})
            return _FakeResponse(200, {
                "Items": [{
                    "Id": "new-item",
                    "Name": "Broken",
                    "Type": "Movie",
                    "MediaSources": [{"Path": "/media/broken.mkv"}],
                }],
            })

    def failing_analyze(item, config):
        raise RuntimeError("scan exploded")

    monkeypatch.setattr(health_scan, "_load_config", fake_load_config)
    monkeypatch.setattr(health_scan, "get_active_media_source", fake_get_source)
    monkeypatch.setattr(health_scan, "get_internal_client", lambda: FakeClient())
    monkeypatch.setattr(health_scan, "_load_library_map", AsyncMock(return_value={}))
    monkeypatch.setattr(health_scan, "_analyze_item", failing_analyze)

    result = await health_scan.run_healthcheck(db_session)

    assert result["error"] == "scan exploded"

    rows = (await db_session.execute(
        select(HealthCheckResult).order_by(HealthCheckResult.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].item_id == "existing"
