"""Library-name resolution: collector precedence + repair routine (#269)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from models.playback_stats import LibraryCache, PlaybackSession
from services.stats_aggregator.libraries import repair_library_names
from services.stats_collector._cache import _item_lib_cache
from services.stats_collector._resolver import (
    _emby_admin_user_id,
    _fetch_ancestors,
    _match_library_name,
    _resolve_library_name,
    _session_library_name,
)
from services.stats_collector.collect import collect_active_sessions

RESOLVER = "services.stats_collector._resolver._resolve_library_name"
GET_CLIENT = "services.stats_collector._resolver.get_internal_client"


@pytest.fixture(autouse=True)
def _clear_lib_cache():
    """The resolver's in-memory cache is module-global — isolate every test."""
    _item_lib_cache.clear()
    yield
    _item_lib_cache.clear()


def _fake_client(ancestors):
    """Stand-in Emby HTTP client whose /Ancestors call returns ``ancestors``."""
    res = SimpleNamespace(status_code=200, json=lambda: ancestors)
    return SimpleNamespace(get=AsyncMock(return_value=res))


@pytest.mark.asyncio
async def test_session_library_prefers_embys_own_library_name():
    """Emby's LibraryName wins outright — the Ancestors API is not even called."""
    resolver = AsyncMock(return_value="Resolved Library")
    with patch(RESOLVER, resolver):
        out = await _session_library_name(
            {"LibraryName": "Movies", "ParentName": "Sub-folder"}, "i1", "http://emby", "k"
        )
    assert out == "Movies"
    resolver.assert_not_awaited()


@pytest.mark.asyncio
async def test_session_library_resolves_collectionfolder_before_parent():
    """No LibraryName → resolve the CollectionFolder, never the parent folder."""
    with patch(RESOLVER, AsyncMock(return_value="Real Library")):
        out = await _session_library_name(
            {"ParentName": "Sub-folder"}, "i1", "http://emby", "k"
        )
    assert out == "Real Library"


@pytest.mark.asyncio
async def test_session_library_uses_parent_only_as_last_resort():
    """ParentName is kept only when Emby gives nothing and resolution fails."""
    with patch(RESOLVER, AsyncMock(return_value=None)):
        out = await _session_library_name(
            {"ParentName": "Sub-folder"}, "i1", "http://emby", "k"
        )
    assert out == "Sub-folder"


@pytest.mark.asyncio
async def test_session_library_none_when_nothing_available():
    with patch(RESOLVER, AsyncMock(return_value=None)):
        out = await _session_library_name({}, "i1", "http://emby", "k")
    assert out is None


def _session(session_key, item_id, library_name):
    return PlaybackSession(
        session_key=session_key,
        user_id="u1",
        user_name="User One",
        item_id=item_id,
        item_name="An Item",
        item_type="Movie",
        library_name=library_name,
    )


@pytest.mark.asyncio
async def test_repair_reresolves_only_non_library_rows(db_session):
    """Rows on a sub-folder/slug or NULL are re-resolved; valid rows untouched."""
    db_session.add(LibraryCache(lib_id="1", name="Movies", collection_type="movies"))
    db_session.add(_session("k1", "i1", "Movies"))      # real library → left alone
    db_session.add(_session("k2", "i2", "Sub-folder"))  # folder → re-resolve
    db_session.add(_session("k3", "i3", None))          # missing → re-resolve
    await db_session.commit()

    with patch(
        "services.stats_aggregator.libraries._repair.get_active_media_source",
        AsyncMock(return_value={"source": "emby", "url": "http://emby", "api_key": "k"}),
    ), patch(
        "services.stats_collector._emby_admin_user_id", AsyncMock(return_value="admin-1"),
    ), patch(
        "services.stats_collector._fetch_ancestors",
        AsyncMock(return_value=[{"Type": "CollectionFolder", "Name": "Movies"}]),
    ) as fetch:
        result = await repair_library_names(db_session)

    assert result["candidates"] == 2
    assert result["migrated"] == 2
    assert fetch.await_count == 2  # the valid row is never re-resolved
    assert fetch.await_args.args[3] == "admin-1"  # admin view threaded to the fetch

    by_key = {
        r.session_key: r.library_name
        for r in (await db_session.execute(select(PlaybackSession))).scalars().all()
    }
    assert by_key == {"k1": "Movies", "k2": "Movies", "k3": "Movies"}


@pytest.mark.asyncio
async def test_repair_is_noop_without_active_emby_source(db_session):
    """Fresh install / no media source configured → no work, no error raised."""
    with patch(
        "services.stats_aggregator.libraries._repair.get_active_media_source",
        AsyncMock(return_value=None),
    ):
        result = await repair_library_names(db_session)
    assert result == {"error": "no_active_media_source"}


@pytest.mark.asyncio
async def test_resolve_uses_cache_by_default():
    """A cached item_id short-circuits — no Emby client is even built."""
    _item_lib_cache["i1"] = "Cached Library"
    client_factory = MagicMock()
    with patch(GET_CLIENT, client_factory):
        out = await _resolve_library_name("i1", "http://emby", "k")
    assert out == "Cached Library"
    client_factory.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_logs_diagnostic_on_folder_fallback(caplog):
    """No CollectionFolder + no alias: return the innermost folder and log the
    ancestry — but do NOT cache the fallback (it is view-dependent)."""
    ancestors = [
        {"Type": "Folder", "Name": "Mystery Folder", "Id": "9"},
        {"Type": "Folder", "Name": "root"},
    ]
    aliases = {"by_id": {}, "by_name": {}}
    client = _fake_client(ancestors)
    with patch(GET_CLIENT, return_value=client), \
            caplog.at_level("WARNING", logger="mediakeeper.stats.collector"):
        out = await _resolve_library_name("i1", "http://emby", "k", aliases)
    assert out == "Mystery Folder"
    assert "i1" not in _item_lib_cache  # fallback slug is not cached
    assert any("no CollectionFolder" in r.getMessage() for r in caplog.records)


# ── _match_library_name (pure) ──────────────────────────────────────────────

def test_match_prefers_collectionfolder():
    ancestors = [
        {"Type": "Folder", "Name": "Sub", "Id": "9"},
        {"Type": "CollectionFolder", "Name": "Movies", "Id": "1"},
    ]
    assert _match_library_name(ancestors) == ("Movies", True)


def test_match_folder_by_id_is_resolved():
    ancestors = [{"Type": "Folder", "Name": "Renamed On Disk", "Id": "42"}]
    aliases = {"by_id": {"42": "Movies"}, "by_name": {}}
    assert _match_library_name(ancestors, aliases) == ("Movies", True)


def test_match_folder_by_name_is_resolved():
    ancestors = [{"Type": "Folder", "Name": "Films", "Id": "8"}]
    aliases = {"by_id": {}, "by_name": {"films": "Films"}}
    assert _match_library_name(ancestors, aliases) == ("Films", True)


def test_match_raw_fallback_is_not_resolved():
    ancestors = [
        {"Type": "Folder", "Name": "Mystery", "Id": "9"},
        {"Type": "Folder", "Name": "root"},
    ]
    assert _match_library_name(ancestors, {"by_id": {}, "by_name": {}}) == ("Mystery", False)


def test_match_nothing_usable():
    assert _match_library_name([{"Type": "Folder", "Name": "root"}]) == (None, False)


# ── _fetch_ancestors ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_ancestors_returns_list_on_200():
    ancestors = [{"Type": "CollectionFolder", "Name": "Movies"}]
    with patch(GET_CLIENT, return_value=_fake_client(ancestors)):
        out = await _fetch_ancestors("i1", "http://emby", "k")
    assert out == ancestors


@pytest.mark.asyncio
async def test_fetch_ancestors_none_on_non_list_payload():
    res = SimpleNamespace(status_code=200, json=lambda: {"not": "a list"})
    client = SimpleNamespace(get=AsyncMock(return_value=res))
    with patch(GET_CLIENT, return_value=client):
        assert await _fetch_ancestors("i1", "http://emby", "k") is None


@pytest.mark.asyncio
async def test_fetch_ancestors_none_on_missing_args():
    assert await _fetch_ancestors("", "http://emby", "k") is None


@pytest.mark.asyncio
async def test_fetch_ancestors_adds_user_id_to_query():
    """A user_id queries the ancestry 'as a user' — the CollectionFolder view."""
    client = _fake_client([{"Type": "CollectionFolder", "Name": "Films"}])
    with patch(GET_CLIENT, return_value=client):
        await _fetch_ancestors("i1", "http://emby", "k", user_id="u42")
    assert client.get.await_args.args[0] == "http://emby/Items/i1/Ancestors?UserId=u42"


@pytest.mark.asyncio
async def test_fetch_ancestors_no_user_id_keeps_plain_query():
    client = _fake_client([])
    with patch(GET_CLIENT, return_value=client):
        await _fetch_ancestors("i1", "http://emby", "k")
    assert client.get.await_args.args[0] == "http://emby/Items/i1/Ancestors"


# ── _emby_admin_user_id ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emby_admin_user_id_prefers_admin():
    users = [
        {"Id": "u1", "Policy": {"IsAdministrator": False}},
        {"Id": "u2", "Policy": {"IsAdministrator": True}},
    ]
    with patch(GET_CLIENT, return_value=_fake_client(users)):
        assert await _emby_admin_user_id("http://emby", "k") == "u2"


@pytest.mark.asyncio
async def test_emby_admin_user_id_falls_back_to_first_user():
    users = [{"Id": "u1", "Policy": {}}, {"Id": "u2", "Policy": {}}]
    with patch(GET_CLIENT, return_value=_fake_client(users)):
        assert await _emby_admin_user_id("http://emby", "k") == "u1"


@pytest.mark.asyncio
async def test_emby_admin_user_id_none_on_empty():
    with patch(GET_CLIENT, return_value=_fake_client([])):
        assert await _emby_admin_user_id("http://emby", "k") is None


# ── collector: intro / trailer exclusion + user_id forwarding ───────────────

@pytest.mark.asyncio
async def test_collect_skips_intro_and_trailer_types(db_session):
    """Non-catalogued playback (Cinema Mode intros = Type 'Video', pre-roll
    trailers = Type 'Trailer') is never tracked; catalogued content is, and the
    session's Emby user id is forwarded to the resolver."""
    sessions = [
        {"UserId": "U1", "UserName": "Alice", "Id": "S1", "PlayState": {},
         "NowPlayingItem": {"Id": "INTRO-1", "Name": "Cinema_intro", "Type": "Video"}},
        {"UserId": "U1", "UserName": "Alice", "Id": "S2", "PlayState": {},
         "NowPlayingItem": {"Id": "TRAILER-1", "Name": "Pre-roll", "Type": "Trailer"}},
        {"UserId": "U9", "UserName": "Bob", "Id": "S3", "PlayState": {},
         "NowPlayingItem": {"Id": "MOVIE-1", "Name": "Coco", "Type": "Movie"}},
        {"UserId": "U9", "UserName": "Bob", "Id": "S4", "PlayState": {},
         "NowPlayingItem": {"Id": "EP-1", "Name": "S01E01", "Type": "Episode"}},
    ]
    seen = []

    def _lib(np, item_id, url, api_key, aliases=None, user_id=None):
        seen.append((item_id, user_id))
        return "Films"

    with patch(
        "services.stats_collector.collect.get_active_media_source",
        new=AsyncMock(return_value={"source": "emby", "url": "http://e", "api_key": "k"}),
    ), patch(
        "services.stats_collector.collect.get_raw_sessions",
        new=AsyncMock(return_value=sessions),
    ), patch(
        "services.stats_collector.collect._session_library_name",
        new=AsyncMock(side_effect=_lib),
    ), patch(
        "services.stats_collector.collect._grant_post_session_xp", new=AsyncMock(),
    ):
        await collect_active_sessions(db_session)

    tracked = {r.item_id for r in (await db_session.execute(select(PlaybackSession))).scalars().all()}
    assert tracked == {"MOVIE-1", "EP-1"}                   # only catalogued content
    assert ("MOVIE-1", "U9") in seen                        # session user id forwarded
    assert all(iid not in ("INTRO-1", "TRAILER-1") for iid, _ in seen)  # skipped pre-resolution


# ── cache / user-view coupling ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_does_not_cache_folder_fallback():
    """A raw-folder fallback (resolved=False) is view-dependent and must NOT be
    cached, so a later per-user resolution isn't served the stale slug."""
    slug_client = _fake_client([
        {"Type": "Folder", "Name": "filmsdanimation", "Id": "9"},
        {"Type": "AggregateFolder", "Name": "root"},
    ])
    with patch(GET_CLIENT, return_value=slug_client):
        out1 = await _resolve_library_name("i1", "http://emby", "k")
    assert out1 == "filmsdanimation"        # returns the fallback
    assert "i1" not in _item_lib_cache       # but does NOT cache it

    real_client = _fake_client([{"Type": "CollectionFolder", "Name": "Films d'Animation"}])
    with patch(GET_CLIENT, return_value=real_client):
        out2 = await _resolve_library_name("i1", "http://emby", "k", user_id="u1")
    assert out2 == "Films d'Animation"       # re-queried, not served the stale slug
    assert _item_lib_cache["i1"] == "Films d'Animation"  # a real library IS cached


@pytest.mark.asyncio
async def test_fetch_ancestors_empty_user_id_keeps_plain_query():
    client = _fake_client([])
    with patch(GET_CLIENT, return_value=client):
        await _fetch_ancestors("i1", "http://emby", "k", user_id="")
    assert client.get.await_args.args[0] == "http://emby/Items/i1/Ancestors"


@pytest.mark.asyncio
async def test_emby_admin_user_id_none_on_non_200():
    res = SimpleNamespace(status_code=500, json=lambda: [])
    with patch(GET_CLIENT, return_value=SimpleNamespace(get=AsyncMock(return_value=res))):
        assert await _emby_admin_user_id("http://emby", "k") is None


@pytest.mark.asyncio
async def test_emby_admin_user_id_none_on_error():
    client = SimpleNamespace(get=AsyncMock(side_effect=RuntimeError("boom")))
    with patch(GET_CLIENT, return_value=client):
        assert await _emby_admin_user_id("http://emby", "k") is None


# ── repair detailed report (manual path) ────────────────────────────────────

@pytest.mark.asyncio
async def test_repair_details_report_unresolved_with_ancestry(db_session):
    """Manual repair over a row Emby can't map to a library reports it unresolved
    (not migrated) and exposes the ancestry for diagnosis."""
    db_session.add(LibraryCache(lib_id="1", name="Movies", collection_type="movies"))
    db_session.add(_session("k2", "i2", "Sub-folder"))
    await db_session.commit()

    ancestors = [
        {"Type": "Folder", "Name": "Sub-folder", "Id": "9"},
        {"Type": "Folder", "Name": "root"},
    ]
    with patch(
        "services.stats_aggregator.libraries._repair.get_active_media_source",
        AsyncMock(return_value={"source": "emby", "url": "http://emby", "api_key": "k"}),
    ), patch(
        "services.stats_collector._emby_admin_user_id", AsyncMock(return_value="admin-1"),
    ), patch("services.stats_collector._fetch_ancestors", AsyncMock(return_value=ancestors)):
        result = await repair_library_names(db_session, collect_details=True)

    assert result["migrated"] == 0
    assert result["unresolved"] == 1
    detail = result["details"][0]
    assert detail["status"] == "unresolved"
    assert detail["ancestors"] == [
        {"type": "Folder", "name": "Sub-folder"},
        {"type": "Folder", "name": "root"},
    ]


@pytest.mark.asyncio
async def test_repair_details_report_migrated(db_session):
    """Manual repair that finds a real library heals the row and reports migrated."""
    db_session.add(LibraryCache(lib_id="1", name="Movies", collection_type="movies"))
    db_session.add(_session("k2", "i2", "Sub-folder"))
    await db_session.commit()

    ancestors = [{"Type": "CollectionFolder", "Name": "Movies", "Id": "1"}]
    with patch(
        "services.stats_aggregator.libraries._repair.get_active_media_source",
        AsyncMock(return_value={"source": "emby", "url": "http://emby", "api_key": "k"}),
    ), patch(
        "services.stats_collector._emby_admin_user_id", AsyncMock(return_value="admin-1"),
    ), patch("services.stats_collector._fetch_ancestors", AsyncMock(return_value=ancestors)):
        result = await repair_library_names(db_session, collect_details=True)

    assert result["migrated"] == 1
    assert result["details"][0]["status"] == "migrated"
    assert result["details"][0]["library_name"] == "Movies"
    row = (await db_session.execute(select(PlaybackSession))).scalar_one()
    assert row.library_name == "Movies"


@pytest.mark.asyncio
async def test_repair_details_report_error(db_session):
    """A per-row Emby failure is caught, counted as error, and surfaced in details."""
    db_session.add(LibraryCache(lib_id="1", name="Movies", collection_type="movies"))
    db_session.add(_session("k2", "i2", "Sub-folder"))
    await db_session.commit()

    with patch(
        "services.stats_aggregator.libraries._repair.get_active_media_source",
        AsyncMock(return_value={"source": "emby", "url": "http://emby", "api_key": "k"}),
    ), patch(
        "services.stats_collector._emby_admin_user_id", AsyncMock(return_value="admin-1"),
    ), patch(
        "services.stats_collector._fetch_ancestors", AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = await repair_library_names(db_session, collect_details=True)

    assert result["errors"] == 1
    assert result["details"][0]["status"] == "error"
