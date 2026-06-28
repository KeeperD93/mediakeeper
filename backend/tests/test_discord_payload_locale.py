"""Discord media payloads re-resolve title/synopsis to the webhook language and
localize the TMDB link label (#288). Emby values are the per-field fallback."""
from __future__ import annotations

import pytest

import services.discord.payloads as pl


@pytest.mark.asyncio
async def test_localized_media_movie(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": f"M{tid}", "overview": f"ov[{locale}]"}

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    out = await pl._localized_media_text(
        {"Name": "Inception", "Overview": "FR"}, "Movie", "27205", "movie", "en", None,
    )
    assert out["name"] == "M27205"
    assert out["overview"] == "ov[en]"


@pytest.mark.asyncio
async def test_localized_media_episode(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "Breaking Bad", "overview": "series ov"}

    async def _ep(tid, s, e, db=None, locale=None):
        return {"name": "Ozymandias", "overview": "ep ov"}

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    monkeypatch.setattr(pl, "get_episode_detail", _ep)
    out = await pl._localized_media_text(
        {"Name": "old", "SeriesName": "oldS", "Overview": "FR",
         "ParentIndexNumber": 5, "IndexNumber": 14},
        "Episode", "1396", "tv", "en", None,
    )
    assert out["series"] == "Breaking Bad"   # series title localized
    assert out["name"] == "Ozymandias"       # episode title localized
    assert out["overview"] == "ep ov"        # episode synopsis localized


@pytest.mark.asyncio
async def test_localized_media_default_lang_keeps_emby(monkeypatch):
    calls = {"n": 0}

    async def _detail(mt, tid, db=None, locale=None):
        calls["n"] += 1
        return {"title": "TMDB title", "overview": "TMDB ov"}

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    out = await pl._localized_media_text(
        {"Name": "Inception", "Overview": "FR syn"}, "Movie", "27205", "movie", "fr", None,
    )
    # Default language -> stored Emby text, no TMDB round-trip.
    assert out == {"name": "Inception", "series": "", "overview": "FR syn"}
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
        return {"title": "Inception", "overview": "ov"}

    async def _img(*a, **k):
        return ""

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    monkeypatch.setattr(pl, "_get_image_url", _img)
    item = {"Type": "Movie", "Name": "Inception", "ProviderIds": {"Tmdb": "27205"}, "ProductionYear": 2010}
    payload = await pl.build_discord_payload(item, {"lang": "en"}, "", "", db=None)
    blob = payload["content"] + str(payload["embeds"])
    assert "TMDB page" in blob
    assert "Fiche TMDB" not in blob


@pytest.mark.asyncio
async def test_payload_label_default_fr(monkeypatch):
    async def _detail(mt, tid, db=None, locale=None):
        return {"title": "Inception", "overview": "ov"}

    async def _img(*a, **k):
        return ""

    monkeypatch.setattr(pl, "get_media_detail", _detail)
    monkeypatch.setattr(pl, "_get_image_url", _img)
    item = {"Type": "Movie", "Name": "Inception", "ProviderIds": {"Tmdb": "27205"}, "ProductionYear": 2010}
    payload = await pl.build_discord_payload(item, {"lang": "fr"}, "", "", db=None)
    blob = payload["content"] + str(payload["embeds"])
    assert "Fiche TMDB" in blob
