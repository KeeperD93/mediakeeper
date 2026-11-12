"""A failed watchlist scan or subtitle audit reports a code to the admin
screens; its exception message stays in the server log."""
from __future__ import annotations

import pytest

from services import subtitle_audit
from services.watchlist_scanner import _state as watchlist_state
from services.watchlist_scanner import scan as watchlist_scan

SECRET = "connection to /data/secret.db failed"


async def _explode(*_args, **_kwargs):
    raise RuntimeError(SECRET)


@pytest.fixture
def fresh_watchlist_state(monkeypatch):
    monkeypatch.setattr(watchlist_state, "_scan_meta", {
        "running": False, "mode": "", "started_at": None, "finished_at": None, "error": None,
    })


@pytest.mark.asyncio
@pytest.mark.parametrize("scan_fn", ["full_scan", "incremental_scan"])
async def test_failed_watchlist_scan_reports_a_code(db_session, monkeypatch, fresh_watchlist_state, scan_fn):
    async def _previous_results(_db):
        return {"series": [{"tmdb_id": 900001, "seasons": []}]}

    monkeypatch.setattr(watchlist_state, "_load_from_db", _previous_results)
    monkeypatch.setattr(watchlist_scan, "_get_all_emby_series", _explode)

    with pytest.raises(RuntimeError):  # the caller still gets, and logs, the real error
        await getattr(watchlist_scan, scan_fn)(db_session)

    status = watchlist_state.get_scan_status()
    assert status["running"] is False
    assert status["error"] == "scan_failed"


@pytest.mark.asyncio
async def test_failed_subtitle_audit_reports_a_code(db_session, monkeypatch, caplog):
    async def _emby_config(_db):
        return ("http://emby.test", "key")

    class _FailingClient:
        get = staticmethod(_explode)

    monkeypatch.setattr("services.emby._get_emby_config", _emby_config)
    monkeypatch.setattr(subtitle_audit, "get_internal_client", lambda: _FailingClient())

    result = await subtitle_audit.run_audit(db_session, languages=["fre"], checks=["missing"])

    assert result == {"error": "audit_failed"}
    assert subtitle_audit.get_audit_progress()["running"] is False
    assert SECRET in caplog.text
