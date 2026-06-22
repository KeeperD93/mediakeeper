"""TMDB runtime cache resolver (services/portal/runtime_cache.py).

Covers the paths #104 relies on:
  * cache hit       → runtime stamped from the DB, no TMDB call
  * cache miss      → one TMDB detail call, runtime persisted + stamped
  * TV series       → runtime taken from the first ``episode_run_time``
  * transient error → nothing stamped, nothing cached (retried later)
Items that already carry a runtime (Emby library cards) or have no
``tmdb_id`` are left untouched.
"""
from datetime import datetime, timedelta, timezone
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
    monkeypatch.setattr(rc, "AsyncSessionLocal", _factory(db_session))
    monkeypatch.setattr(rc, "_tmdb_headers_sync", lambda _k: {})
    monkeypatch.setattr(rc, "get_external_client", lambda: _FakeClient({"runtime": 999}))

    fetched = await rc._fetch_and_store([(88888, "movie")], "key")

    assert fetched == {(88888, "movie"): 999}  # returns the freshly fetched value
    row = (await db_session.execute(
        select(TmdbRuntimeCache).where(TmdbRuntimeCache.tmdb_id == 88888)
    )).scalar_one()  # exactly one row, the original — insert was a no-op
    assert row.runtime == 120  # a real runtime is immutable, not overwritten


@pytest.mark.asyncio
async def test_resolve_runtimes_sorts_misses_for_deterministic_lock_order(db_session, monkeypatch):
    """Misses are handed to the persister in a deterministic (sorted) order so
    concurrent renders acquire the unique-index locks identically and cannot
    cross-lock into a Postgres deadlock."""
    monkeypatch.setattr(rc, "AsyncSessionLocal", _factory(db_session))
    monkeypatch.setattr(rc, "_get_tmdb_key", AsyncMock(return_value="key"))
    captured = {}

    async def _capture(misses, api_key):
        captured["misses"] = list(misses)
        return {}

    monkeypatch.setattr(rc, "_fetch_and_store", _capture)

    items = [
        {"tmdb_id": 300, "media_type": "movie"},
        {"tmdb_id": 100, "media_type": "tv"},
        {"tmdb_id": 200, "media_type": "movie"},
    ]
    await rc.resolve_runtimes(items)

    assert captured["misses"] == [(100, "tv"), (200, "movie"), (300, "movie")]


@pytest.mark.asyncio
async def test_resolve_runtimes_refetches_stale_zero(db_session, monkeypatch):
    # A cached "absent" runtime (0) older than the TTL is re-resolved in place:
    # an upcoming title that now has a duration on TMDB gets picked up.
    stale = datetime.now(timezone.utc) - timedelta(days=rc._ZERO_RUNTIME_TTL_DAYS + 1)
    db_session.add(TmdbRuntimeCache(
        tmdb_id=99001, media_type="movie", runtime=0, fetched_at=stale,
    ))
    await db_session.commit()
    _mock_tmdb(monkeypatch, db_session, _FakeClient({"runtime": 110}))

    items = [{"tmdb_id": 99001, "media_type": "movie", "title": "Now Known"}]
    await rc.resolve_runtimes(items)

    assert items[0]["runtime"] == 110
    row = (await db_session.execute(
        select(TmdbRuntimeCache).where(TmdbRuntimeCache.tmdb_id == 99001)
    )).scalar_one()  # same row, refreshed in place
    assert row.runtime == 110


@pytest.mark.asyncio
async def test_resolve_runtimes_keeps_fresh_zero_without_refetch(db_session, monkeypatch):
    # A fresh "absent" runtime (0 within the TTL) is trusted: no TMDB call.
    db_session.add(TmdbRuntimeCache(
        tmdb_id=99002, media_type="movie", runtime=0,
        fetched_at=datetime.now(timezone.utc),
    ))
    await db_session.commit()

    calls = {"n": 0}

    class _CountingClient(_FakeClient):
        async def get(self, *a, **k):
            calls["n"] += 1
            return await super().get(*a, **k)

    _mock_tmdb(monkeypatch, db_session, _CountingClient({"runtime": 110}))

    items = [{"tmdb_id": 99002, "media_type": "movie", "title": "Fresh Zero"}]
    await rc.resolve_runtimes(items)

    assert "runtime" not in items[0]  # still absent, not stamped
    assert calls["n"] == 0  # fresh 0 trusted → no re-fetch


@pytest.mark.asyncio
async def test_resolve_runtimes_rearms_stale_zero_when_still_absent(db_session, monkeypatch):
    # Anti-hammering: a stale "absent" (0) re-resolved while TMDB still has no
    # runtime stays 0 but gets fetched_at re-armed to now, so the next render
    # trusts it as fresh instead of re-hitting TMDB forever. A regression that
    # dropped the fetched_at=now from the <=0 UPDATE would leave it stale and
    # re-fetch every render — this test would then go red.
    stale = datetime.now(timezone.utc) - timedelta(days=rc._ZERO_RUNTIME_TTL_DAYS + 1)
    db_session.add(TmdbRuntimeCache(
        tmdb_id=99003, media_type="movie", runtime=0, fetched_at=stale,
    ))
    await db_session.commit()
    _mock_tmdb(monkeypatch, db_session, _FakeClient({"runtime": 0}))  # still absent

    items = [{"tmdb_id": 99003, "media_type": "movie", "title": "Still Absent"}]
    await rc.resolve_runtimes(items)

    assert "runtime" not in items[0]  # still 0 → not stamped
    cutoff = datetime.now(timezone.utc) - timedelta(days=rc._ZERO_RUNTIME_TTL_DAYS)
    row = (await db_session.execute(
        select(TmdbRuntimeCache).where(TmdbRuntimeCache.tmdb_id == 99003)
    )).scalar_one()
    assert row.runtime == 0  # unchanged
    assert rc._as_utc(row.fetched_at) >= cutoff  # re-armed → fresh, no re-fetch next render
