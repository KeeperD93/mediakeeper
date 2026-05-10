"""Discord template dispatch tests for the added-media notification flow.

Covers two related concerns:
  * the configured admin template (color, ``<synopsis>``, ``<tmdb>``) is
    actually rendered into the Discord payload — i.e. no hardcoded
    string slips through;
  * a synthetic ``Grouped`` batch is promoted to ``Series`` / ``Season``
    when the Emby state shows the batch is more than just episode
    fill-in, so the right ``added_*`` template is picked.
"""
import pytest

from services.discord.payloads import build_discord_payload
from services.notification_engine._classify import (
    classify_grouped,
    promote_grouped_items,
)


def _wh_with_template(tpl_key: str, template: str, color: str = "#ff5500"):
    return {
        "url": "https://discord.com/api/webhooks/1/secret",
        "lang": "fr",
        "templates": {tpl_key: template},
        "settings": {tpl_key: {"color": color, "image_style": "thumbnail"}},
    }


@pytest.mark.asyncio
async def test_discord_template_synopsis_substituted():
    item = {
        "Type": "Series",
        "Name": "Test Show",
        "Overview": "A spy thriller about geometry teachers.",
        "ProviderIds": {"Tmdb": "12345"},
        "ProductionYear": 2026,
        "ChildCount": 3,
    }
    wh = _wh_with_template(
        "added_series",
        "📺 Une nouvelle série est disponible !\n\n**<titre> (<annee>)**\n\n<synopsis>\n\nVoir les détails\n<tmdb>",
    )
    payload = await build_discord_payload(
        item, wh, emby_url="http://emby", emby_api_key="k",
    )
    description = payload["embeds"][0]["description"]
    assert "A spy thriller about geometry teachers." in description


@pytest.mark.asyncio
async def test_discord_template_color_used():
    item = {
        "Type": "Movie",
        "Name": "Demo",
        "Overview": "x",
        "ProviderIds": {"Tmdb": "1"},
        "ProductionYear": 2026,
    }
    wh = _wh_with_template(
        "added_movie",
        "🎬 ajout\n\n**<titre>**\n\n<synopsis>",
        color="#ff5500",
    )
    payload = await build_discord_payload(
        item, wh, emby_url="http://emby", emby_api_key="k",
    )
    assert payload["embeds"][0]["color"] == 0xFF5500


@pytest.mark.asyncio
async def test_discord_template_tmdb_url_resolved_for_series():
    item = {
        "Type": "Series",
        "Name": "Demo Series",
        "Overview": "x",
        "ProviderIds": {"Tmdb": "9876"},
        "ProductionYear": 2026,
    }
    wh = _wh_with_template(
        "added_series",
        "x\n\n**<titre>**\n\n<synopsis>\n\n<tmdb>",
    )
    payload = await build_discord_payload(
        item, wh, emby_url="http://emby", emby_api_key="k",
    )
    description = payload["embeds"][0]["description"]
    assert "https://www.themoviedb.org/tv/9876" in description


@pytest.mark.asyncio
async def test_grouped_promoted_to_series_when_full_series_in_batch(monkeypatch):
    item = {
        "Type": "Grouped",
        "SeriesName": "Brand New",
        "SeriesId": "S100",
        "IndexNumber": 1,
        "ChildCount": 8,
        "ProviderIds": {"Tmdb": "111"},
        "Overview": "placeholder",
    }
    # Emby shows exactly the 8 episodes from this batch — the series is
    # brand-new in the library.
    eps = {(1, n) for n in range(1, 9)}

    async def fake_eps(_db, _series_id):
        return eps

    async def fake_fetch(_db, _series_id):
        return {
            "Overview": "real series synopsis",
            "ProductionYear": 2026,
            "ProviderIds": {"Tmdb": "111"},
        }

    monkeypatch.setattr(
        "services.notification_engine._classify._get_emby_episodes", fake_eps,
    )
    monkeypatch.setattr(
        "services.notification_engine._classify.fetch_item_by_id", fake_fetch,
    )

    items = [item]
    await promote_grouped_items(items, db=None)
    assert items[0]["Type"] == "Series"
    assert items[0]["Overview"] == "real series synopsis"


@pytest.mark.asyncio
async def test_grouped_promoted_to_season_when_full_season_in_batch(monkeypatch):
    item = {
        "Type": "Grouped",
        "SeriesName": "Existing Show",
        "SeriesId": "S200",
        "IndexNumber": 2,
        "ChildCount": 6,
        "ProviderIds": {"Tmdb": "222"},
        "Overview": "placeholder",
    }
    # Season 1 is already there (10 eps); season 2 is exactly the batch.
    eps = {(1, n) for n in range(1, 11)} | {(2, n) for n in range(1, 7)}

    async def fake_eps(_db, _series_id):
        return eps

    async def fake_fetch(_db, _series_id):
        return {
            "Overview": "season synopsis",
            "ProductionYear": 2026,
            "ProviderIds": {"Tmdb": "222"},
        }

    monkeypatch.setattr(
        "services.notification_engine._classify._get_emby_episodes", fake_eps,
    )
    monkeypatch.setattr(
        "services.notification_engine._classify.fetch_item_by_id", fake_fetch,
    )

    items = [item]
    await promote_grouped_items(items, db=None)
    assert items[0]["Type"] == "Season"


@pytest.mark.asyncio
async def test_grouped_falls_back_when_partial_season(monkeypatch):
    # Three episodes in a season that already has more — partial fill.
    item = {
        "Type": "Grouped",
        "SeriesName": "Existing Show",
        "SeriesId": "S300",
        "IndexNumber": 3,
        "ChildCount": 3,
        "ProviderIds": {"Tmdb": "333"},
        "Overview": "placeholder",
    }
    eps = {(3, n) for n in range(1, 11)}  # 10 eps total in season 3

    async def fake_eps(_db, _series_id):
        return eps

    monkeypatch.setattr(
        "services.notification_engine._classify._get_emby_episodes", fake_eps,
    )

    new_type = await classify_grouped(item, db=None)
    assert new_type == "Grouped"


@pytest.mark.asyncio
async def test_grouped_payload_exposes_synopsis_variable():
    """Even before promotion, an admin-customised ``added_grouped``
    template that references ``<synopsis>`` must resolve."""
    item = {
        "Type": "Grouped",
        "Name": "Grouped Show",
        "SeriesName": "Grouped Show",
        "SeriesId": "S400",
        "Id": "S400",
        "IndexNumber": 1,
        "ChildCount": 4,
        "ProviderIds": {"Tmdb": "444"},
        "Overview": "an unusual late-night batch synopsis",
    }
    wh = _wh_with_template(
        "added_grouped",
        "▶️ batch\n\n**<titre_serie>**\n\n<synopsis>\n\n<nb_episodes> eps",
    )
    payload = await build_discord_payload(
        item, wh, emby_url="http://emby", emby_api_key="k",
    )
    description = payload["embeds"][0]["description"]
    assert "an unusual late-night batch synopsis" in description
