"""The daily digest follows the viewer's active locale (X-MK-Locale): the
recent-additions block re-resolves Emby titles, and the endpoint reads the
canonical locale channel instead of Accept-Language only (#288)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.portal import available_localize as al
from services.portal import daily_digest as dd
from services.portal import daily_digest_sources as sources
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


def _patch_localize(monkeypatch):
    al._meta_cache.clear()

    async def _key(db=None):
        return "test-key"

    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"T{tid} [{locale}]", "overview": "o"}

    monkeypatch.setattr("services.portal.available_localize._get_tmdb_key", _key)
    monkeypatch.setattr("services.portal.available_localize.get_media_detail", _detail)


@pytest.mark.asyncio
async def test_recent_adds_localizes_titles(db_session, monkeypatch):
    async def _recent(db, limit=80):
        return [{
            "tmdb_id": 603, "media_type": "movie", "title": "Matrice",
            "emby_item_id": "x", "year": "1999", "poster_url": "",
            "date_created": "2099-01-01",
        }]

    monkeypatch.setattr("services.portal.daily_digest_sources.get_recently_added", _recent)
    _patch_localize(monkeypatch)

    since = datetime(2000, 1, 1, tzinfo=timezone.utc)
    result = await sources.recent_adds(db_session, since=since, lang="en")
    assert result[0]["title"] == "T603 [en]"


@pytest.mark.asyncio
async def test_recent_adds_default_locale_noop(db_session, monkeypatch):
    async def _recent(db, limit=80):
        return [{
            "tmdb_id": 603, "media_type": "movie", "title": "Matrice",
            "emby_item_id": "x", "year": "1999", "poster_url": "",
            "date_created": "2099-01-01",
        }]

    monkeypatch.setattr("services.portal.daily_digest_sources.get_recently_added", _recent)
    _patch_localize(monkeypatch)

    since = datetime(2000, 1, 1, tzinfo=timezone.utc)
    result = await sources.recent_adds(db_session, since=since, lang="fr")
    assert result[0]["title"] == "Matrice"


@pytest.mark.asyncio
async def test_recent_adds_degrades_on_localize_failure(db_session, monkeypatch):
    """A TMDB/DB hiccup during localization degrades to the stored titles
    rather than bubbling up and 500-ing the whole digest."""
    async def _recent(db, limit=80):
        return [{
            "tmdb_id": 603, "media_type": "movie", "title": "Matrice",
            "emby_item_id": "x", "year": "1999", "poster_url": "",
            "date_created": "2099-01-01",
        }]

    async def _boom(db, items, locale):
        raise RuntimeError("tmdb down")

    monkeypatch.setattr("services.portal.daily_digest_sources.get_recently_added", _recent)
    monkeypatch.setattr("services.portal.daily_digest_sources.localize_emby_items", _boom)

    since = datetime(2000, 1, 1, tzinfo=timezone.utc)
    result = await sources.recent_adds(db_session, since=since, lang="en")
    assert result[0]["title"] == "Matrice"  # degraded to the stored title


@pytest.mark.asyncio
async def test_digest_endpoint_uses_request_locale(client, db_session, monkeypatch):
    user, _ = await make_portal_user(db_session, username="digest-i18n", display_name="V", role="viewer")
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    captured = {}

    async def _dismissed(db, uid):
        return False

    async def _build(db, u, *, use_cache=True, lang="fr"):
        captured["lang"] = lang
        return {"empty": True, "recent_adds": []}

    monkeypatch.setattr("services.portal.daily_digest.is_dismissed_today", _dismissed)
    monkeypatch.setattr("services.portal.daily_digest.build_digest", _build)

    r = await client.get("/api/portal/daily-digest", headers={"X-MK-Locale": "en"})
    assert r.status_code == 200, r.text
    assert captured["lang"] == "en"


@pytest.mark.asyncio
async def test_build_digest_caches_per_lang(db_session, monkeypatch):
    """The 1h cache key includes the viewer locale: two languages produce two
    distinct entries, so an `en` viewer is never served the `fr` payload cached
    moments earlier by another locale (regression introduced with #288)."""
    user, _ = await make_portal_user(db_session, username="digest-cache", display_name="V", role="viewer")
    dd._digest_cache.clear()

    async def _recent(db, since, lang="fr"):
        return [{"title": f"add [{lang}]"}]

    async def _events(db, uid):
        return []

    async def _ranking(db, u, lang="fr"):
        return {"position": 0}

    async def _quota(db, uid):
        return {"used": 0}

    async def _tickets(db, uid):
        return 0

    async def _streak(db, u, p):
        return 0

    async def _ach(db, uid):
        return None

    monkeypatch.setattr("services.portal.daily_digest.sources.recent_adds", _recent)
    monkeypatch.setattr("services.portal.daily_digest.sources.upcoming_events", _events)
    monkeypatch.setattr("services.portal.daily_digest.sources.ranking_snapshot", _ranking)
    monkeypatch.setattr("services.portal.daily_digest.sources.quota_snapshot", _quota)
    monkeypatch.setattr("services.portal.daily_digest.sources.open_tickets_count", _tickets)
    monkeypatch.setattr("services.portal.daily_digest.sources.current_streak", _streak)
    monkeypatch.setattr("services.portal.daily_digest.sources.closest_achievement", _ach)
    monkeypatch.setattr("services.portal.daily_digest.sources.level_info", lambda p: {"xp": 0})

    fr = await dd.build_digest(db_session, user, lang="fr")
    en = await dd.build_digest(db_session, user, lang="en")
    assert fr["recent_adds"] == [{"title": "add [fr]"}]
    assert en["recent_adds"] == [{"title": "add [en]"}]

    user_keys = {k for k in dd._digest_cache if k[0] == user.id}
    assert len(user_keys) == 2
    assert {k[2] for k in user_keys} == {"fr", "en"}
    # A cached re-read serves the locale-correct payload, not the first one cached.
    again = await dd.build_digest(db_session, user, lang="fr")
    assert again["recent_adds"] == [{"title": "add [fr]"}]
    dd._digest_cache.clear()
