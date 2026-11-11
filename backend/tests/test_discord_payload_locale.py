"""Discord media payloads re-resolve title/synopsis to the webhook language and
localize the TMDB link label. Emby values are the per-field fallback."""
from __future__ import annotations

import pytest

import services.discord.payloads as pl


@pytest.mark.asyncio
async def test_localized_media_movie(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"M{tid}", "overview": f"ov[{locale}]"}

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    out = await pl._localized_media_text(
        {"Name": "Sample Movie", "Overview": "FR"}, "Movie", "900001", "movie", "en", None,
    )
    assert out["name"] == "M900001"
    assert out["overview"] == "ov[en]"


@pytest.mark.asyncio
async def test_localized_media_episode(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "Sample Show", "overview": "series ov"}

    async def _ep(tid, s, e, db=None, locale=None):
        return {"name": "Sample Episode", "overview": "ep ov"}

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    monkeypatch.setattr(pl, "get_episode_detail", _ep)
    out = await pl._localized_media_text(
        {"Name": "old", "SeriesName": "oldS", "Overview": "FR",
         "ParentIndexNumber": 5, "IndexNumber": 14},
        "Episode", "900002", "tv", "en", None,
    )
    assert out["series"] == "Sample Show"    # series title localized
    assert out["name"] == "Sample Episode"   # episode title localized
    assert out["overview"] == "ep ov"        # episode synopsis localized


@pytest.mark.asyncio
async def test_localized_media_default_lang_keeps_emby(monkeypatch):
    calls = {"n": 0}

    async def _detail(mt, tid, db=None, locale=None):
        calls["n"] += 1
        return {"title": "TMDB title", "overview": "TMDB ov"}

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    out = await pl._localized_media_text(
        {"Name": "Sample Movie", "Overview": "FR syn"}, "Movie", "900001", "movie", "fr", None,
    )
    # Default language -> stored Emby text, no TMDB round-trip.
    assert out == {"name": "Sample Movie", "series": "", "overview": "FR syn"}
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_localized_media_no_tmdb_id():
    out = await pl._localized_media_text(
        {"Name": "X", "Overview": "FR"}, "Movie", None, "movie", "en", None,
    )
    assert out == {"name": "X", "series": "", "overview": "FR"}


@pytest.mark.asyncio
async def test_payload_label_localized_en(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "Sample Movie", "overview": "ov"}

    async def _img(*a, **k):
        return ""

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    monkeypatch.setattr(pl, "_get_image_url", _img)
    item = {"Type": "Movie", "Name": "Sample Movie", "ProviderIds": {"Tmdb": "900001"}, "ProductionYear": 2020}
    payload = await pl.build_discord_payload(item, {"lang": "en"}, "", "", db=None)
    blob = payload["content"] + str(payload["embeds"])
    assert "TMDB page" in blob
    assert "Fiche TMDB" not in blob


@pytest.mark.asyncio
async def test_payload_label_default_fr(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "Sample Movie", "overview": "ov"}

    async def _img(*a, **k):
        return ""

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    monkeypatch.setattr(pl, "_get_image_url", _img)
    item = {"Type": "Movie", "Name": "Sample Movie", "ProviderIds": {"Tmdb": "900001"}, "ProductionYear": 2020}
    payload = await pl.build_discord_payload(item, {"lang": "fr"}, "", "", db=None)
    blob = payload["content"] + str(payload["embeds"])
    assert "Fiche TMDB" in blob
