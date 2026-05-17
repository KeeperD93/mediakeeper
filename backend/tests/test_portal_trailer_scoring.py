"""Scoring rules used by ``_pick_video`` (portal trailers cascade, bug #99).

The hero banner picks the trailer language via a cascade
``user_language → en → original → null`` (see ``_resolve_tmdb_trailer``),
but within a single language bucket several candidate videos can match.
The picker must surface the publisher's *official Trailer* — newest if
several exist — over older Teasers or fan-uploaded VOSTFR cuts, which
the hero banner would otherwise stream silently.
"""
from __future__ import annotations

from services.portal.trailers import _pick_video


def _video(
    *,
    key: str,
    lang: str = "fr",
    type_: str = "Trailer",
    official: bool = True,
    published_at: str = "2024-01-01T00:00:00.000Z",
    site: str = "YouTube",
) -> dict:
    return {
        "key": key,
        "iso_639_1": lang,
        "type": type_,
        "official": official,
        "published_at": published_at,
        "site": site,
        "name": f"video {key}",
    }


def test_pick_video_prefers_trailer_over_teaser():
    teaser = _video(key="OLD-TEASER", type_="Teaser")
    trailer = _video(key="THE-TRAILER", type_="Trailer")

    picked = _pick_video([teaser, trailer], "fr")

    assert picked["key"] == "THE-TRAILER"


def test_pick_video_prefers_official_over_fan_upload():
    fan = _video(key="FAN-VOSTFR", official=False)
    official = _video(key="OFFICIAL-VF", official=True)

    # Fan upload listed first to make sure ordering isn't the tie-breaker.
    picked = _pick_video([fan, official], "fr")

    assert picked["key"] == "OFFICIAL-VF"


def test_pick_video_prefers_most_recent_official_trailer():
    old = _video(key="OLD-VF", published_at="2022-05-01T00:00:00.000Z")
    new = _video(key="NEW-VF", published_at="2024-09-01T00:00:00.000Z")

    picked = _pick_video([old, new], "fr")

    assert picked["key"] == "NEW-VF"


def test_pick_video_trailer_official_old_beats_fan_recent():
    """Type + official outweigh recency — the franchise's own dub wins
    even if a fresher fan-uploaded teaser landed last week."""
    old_official_trailer = _video(
        key="STUDIO-VF",
        type_="Trailer",
        official=True,
        published_at="2022-01-01T00:00:00.000Z",
    )
    new_fan_teaser = _video(
        key="FAN-TEASER",
        type_="Teaser",
        official=False,
        published_at="2024-12-01T00:00:00.000Z",
    )

    picked = _pick_video([new_fan_teaser, old_official_trailer], "fr")

    assert picked["key"] == "STUDIO-VF"


def test_pick_video_skips_non_youtube_vimeo_sites():
    facebook = _video(key="FB-VIDEO", site="Facebook")
    youtube = _video(key="YT-VIDEO")

    picked = _pick_video([facebook, youtube], "fr")

    assert picked["key"] == "YT-VIDEO"


def test_pick_video_filters_by_language_when_provided():
    fr = _video(key="FR-TRAILER", lang="fr")
    en = _video(key="EN-TRAILER", lang="en")

    assert _pick_video([fr, en], "en")["key"] == "EN-TRAILER"
    assert _pick_video([fr, en], "fr")["key"] == "FR-TRAILER"


def test_pick_video_accepts_any_language_with_none():
    en = _video(key="EN-TRAILER", lang="en")
    fr = _video(key="FR-TRAILER", lang="fr")

    picked = _pick_video([en, fr], None)

    assert picked is not None
    assert picked["key"] in {"EN-TRAILER", "FR-TRAILER"}


def test_pick_video_returns_none_when_empty():
    assert _pick_video([], "fr") is None
    assert _pick_video([_video(key="X", site="Facebook")], "fr") is None
