"""TMDB runtime cache resolver (services/portal/runtime_cache.py).

Covers the paths #104 relies on:
  * cache hit       → runtime stamped from the DB, no TMDB call
  * cache miss      → one TMDB detail call, runtime persisted + stamped
  * TV series       → runtime taken from the first ``episode_run_time``
  * transient error → nothing stamped, nothing cached (retried later)
Items that already carry a runtime (Emby library cards) or have no
``tmdb_id`` are left untouched.
"""
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

import services.portal.runtime_cache as rc
from models.portal.tmdb_runtime import TmdbRuntimeCache


def _factory(db_session):
    """Sessionmaker on the same in-memory engine the fixture uses, so the
    resolver's own short-lived session sees rows the test committed."""
    return sessionmaker(
        bind=db_session.bind, class_=AsyncSession, expire_on_commit=False,
    )


class _FakeClient:
    """Stand-in for the external httpx client — returns a fixed TMDB detail
    payload + status for every ``get``."""
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status

    async def get(self, *_a, **_k):
        payload, status = self._payload, self._status

        class _Resp:
            status_code = status

            @staticmethod
            def json():
                return payload

        return _Resp()


def _mock_tmdb(monkeypatch, db_session, client):
    monkeypatch.setattr(rc, "AsyncSessionLocal", _factory(db_session))
    monkeypatch.setattr(rc, "_get_tmdb_key", AsyncMock(return_value="key"))
    monkeypatch.setattr(rc, "_tmdb_headers_sync", lambda _k: {})
    monkeypatch.setattr(rc, "get_external_client", lambda: client)


@pytest.mark.asyncio
async def test_resolve_runtimes_stamps_from_cache(db_session, monkeypatch):
    db_session.add(TmdbRuntimeCache(tmdb_id=603, media_type="movie", runtime=136))
    await db_session.commit()
    monkeypatch.setattr(rc, "AsyncSessionLocal", _factory(db_session))

    items = [
        {"tmdb_id": 603, "media_type": "movie", "title": "Cached Movie"},
        {"tmdb_id": 1, "media_type": "tv", "title": "Already", "runtime": 42},
        {"tmdb_id": None, "media_type": "movie", "title": "No id"},
    ]
    await rc.resolve_runtimes(items)

    assert items[0]["runtime"] == 136   # filled from the persistent cache
    assert items[1]["runtime"] == 42    # untouched — already carried a runtime
    assert "runtime" not in items[2]    # no tmdb_id → skipped


@pytest.mark.asyncio
async def test_resolve_runtimes_fetches_and_persists_on_miss(db_session, monkeypatch):
    _mock_tmdb(monkeypatch, db_session, _FakeClient({"runtime": 148}))

    items = [{"tmdb_id": 27205, "media_type": "movie", "title": "Miss Movie"}]
    await rc.resolve_runtimes(items)

    assert items[0]["runtime"] == 148
    row = (await db_session.execute(
        select(TmdbRuntimeCache).where(TmdbRuntimeCache.tmdb_id == 27205)
    )).scalar_one()
    assert row.runtime == 148


@pytest.mark.asyncio
async def test_resolve_runtimes_tv_uses_first_episode_run_time(db_session, monkeypatch):
    _mock_tmdb(monkeypatch, db_session, _FakeClient({"episode_run_time": [52, 48]}))

    items = [{"tmdb_id": 1399, "media_type": "tv", "title": "Series"}]
    await rc.resolve_runtimes(items)

    assert items[0]["runtime"] == 52  # first episode_run_time entry


@pytest.mark.asyncio
async def test_resolve_runtimes_transient_failure_not_cached(db_session, monkeypatch):
    _mock_tmdb(monkeypatch, db_session, _FakeClient({}, status=503))

    items = [{"tmdb_id": 55555, "media_type": "movie", "title": "Flaky"}]
    await rc.resolve_runtimes(items)

    assert "runtime" not in items[0]  # degraded silently, no stamp
    # A transient failure must NOT be cached so a later render can retry.
    cached = (await db_session.execute(
        select(TmdbRuntimeCache).where(TmdbRuntimeCache.tmdb_id == 55555)
    )).scalar_one_or_none()
    assert cached is None


@pytest.mark.asyncio
async def test_resolve_runtimes_zero_runtime_persisted_but_not_stamped(db_session, monkeypatch):
    # TMDB reports a movie with runtime 0 (genuinely no runtime): the 0 is
    # cached (distinct from a transient None) but never stamped onto the card.
    _mock_tmdb(monkeypatch, db_session, _FakeClient({"runtime": 0}))

    items = [{"tmdb_id": 77777, "media_type": "movie", "title": "Zero"}]
    await rc.resolve_runtimes(items)

    assert "runtime" not in items[0]  # falsy 0 is not stamped (no "0 min" badge)
    row = (await db_session.execute(
        select(TmdbRuntimeCache).where(TmdbRuntimeCache.tmdb_id == 77777)
    )).scalar_one()
    assert row.runtime == 0  # cached so it is not re-fetched every render


@pytest.mark.asyncio
async def test_fetch_and_store_swallows_concurrent_insert_race(db_session, monkeypatch):
    # Simulate the race: the row already exists when _fetch_and_store tries to
    # insert it (a concurrent render won). The UniqueConstraint violation must
    # be swallowed via begin_nested, the commit must still succeed, and the
    # pre-existing row must be left intact.
    db_session.add(TmdbRuntimeCache(tmdb_id=88888, media_type="movie", runtime=120))
    await db_session.commit()
    monkeypatch.setattr(rc, "_get_tmdb_key", AsyncMock(return_value="key"))
    monkeypatch.setattr(rc, "_tmdb_headers_sync", lambda _k: {})
    monkeypatch.setattr(rc, "get_external_client", lambda: _FakeClient({"runtime": 999}))

    fetched = await rc._fetch_and_store(db_session, [(88888, "movie")])

    assert fetched == {(88888, "movie"): 999}  # returns the freshly fetched value
    row = (await db_session.execute(
        select(TmdbRuntimeCache).where(TmdbRuntimeCache.tmdb_id == 88888)
    )).scalar_one()  # exactly one row, the original — insert was a no-op
    assert row.runtime == 120
