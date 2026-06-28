"""Scoring rules used by ``_pick_video`` (portal trailers cascade, bug #99).

The hero banner picks the trailer language via a cascade
``user_language → en → original → null`` (see ``_resolve_tmdb_trailer``),
but within a single language bucket several candidate videos can match.
The picker must surface the publisher's *official Trailer* — newest if
several exist — over older Teasers or fan-uploaded VOSTFR cuts, which
the hero banner would otherwise stream silently.
"""
from __future__ import annotations

from services.portal.trailers import _pick_video, _rank_videos


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


def test_pick_video_boosts_officielle_over_other_fr_trailer():
    """Two same-rank Trailer official fr videos: the one whose name
    contains ``officielle`` wins over a neutral-named one."""
    neutral = _video(
        key="NEUTRAL-VF",
        published_at="2024-01-01T00:00:00.000Z",
    )
    neutral["name"] = "Trailer"
    officielle = _video(
        key="OFFICIELLE-VF",
        published_at="2024-01-01T00:00:00.000Z",
    )
    officielle["name"] = "Bande-annonce officielle"

    picked = _pick_video([neutral, officielle], "fr")

    assert picked["key"] == "OFFICIELLE-VF"


def test_pick_video_fr_prefers_bande_annonce_over_trailer_word():
    """At the fr step, a video named ``Bande annonce`` outranks a
    same-rank video named ``Trailer`` (English label) — the French
    audience expects the French-labelled cut."""
    en_word = _video(key="EN-WORD", published_at="2024-01-01T00:00:00.000Z")
    en_word["name"] = "Trailer"
    fr_word = _video(key="FR-WORD", published_at="2024-01-01T00:00:00.000Z")
    fr_word["name"] = "Bande annonce"

    picked = _pick_video([en_word, fr_word], "fr")

    assert picked["key"] == "FR-WORD"


def test_pick_video_en_prefers_trailer_word_over_bande_annonce():
    """Symmetric: at the en step, ``Trailer`` outranks ``Bande annonce``
    even if both videos are tagged en (TMDB occasionally mistags)."""
    fr_word = _video(key="FR-WORD", lang="en", published_at="2024-01-01T00:00:00.000Z")
    fr_word["name"] = "Bande annonce"
    en_word = _video(key="EN-WORD", lang="en", published_at="2024-01-01T00:00:00.000Z")
    en_word["name"] = "Trailer"

    picked = _pick_video([fr_word, en_word], "en")

    assert picked["key"] == "EN-WORD"


def test_pick_video_penalises_vo_abbreviation():
    """A bare ``VO`` / ``V.O.`` (Version Originale) in the title acts as
    a penalty — signals undubbed content even on iso_639_1=fr."""
    dub = _video(key="DUB-VF", published_at="2024-01-01T00:00:00.000Z")
    dub["name"] = "Bande annonce officielle"
    vo = _video(key="VO-FR", published_at="2024-01-01T00:00:00.000Z")
    vo["name"] = "Bande annonce VO"

    picked = _pick_video([vo, dub], "fr")

    assert picked["key"] == "DUB-VF"


def test_pick_video_vo_regex_ignores_video_voice_over():
    """The VO penalty must not fire on substrings like ``video`` or
    ``voice over``: both contain ``v`` next to ``o`` somewhere but
    neither is the abbreviation itself."""
    safe_video = _video(key="SAFE", published_at="2024-01-01T00:00:00.000Z")
    safe_video["name"] = "video diary, voice over"

    # Confidence check: same name with a bare "VO" must lose.
    flagged = _video(key="FLAGGED", published_at="2024-02-01T00:00:00.000Z")
    flagged["name"] = "voice over and VO too"

    picked = _pick_video([safe_video, flagged], "fr")

    assert picked["key"] == "SAFE"


def test_pick_video_penalises_version_originale():
    """``Version originale`` in the title is a penalty regardless of the
    iso_639_1 bucket."""
    vo = _video(key="VO-VERSION", published_at="2024-12-01T00:00:00.000Z")
    vo["name"] = "Trailer Version originale sous-titrée"
    dub = _video(key="DUB", published_at="2023-01-01T00:00:00.000Z")
    dub["name"] = "Bande annonce officielle"

    picked = _pick_video([vo, dub], "fr")

    assert picked["key"] == "DUB"


def test_pick_video_fr_boosts_bare_vf_abbreviation():
    """The ``VF`` abbreviation (Version Française) acts as a boost at the
    fr step — common on TMDB ('Trailer VF', 'Bande-annonce VF'). The
    word-boundary regex must not collide with ``VFX``."""
    plain = _video(key="PLAIN", published_at="2024-01-01T00:00:00.000Z")
    plain["name"] = "Trailer"
    vf = _video(key="VF-CUT", published_at="2024-01-01T00:00:00.000Z")
    vf["name"] = "Trailer VF"
    vfx = _video(key="VFX-REEL", published_at="2024-02-01T00:00:00.000Z")
    vfx["name"] = "VFX breakdown"

    picked = _pick_video([plain, vf, vfx], "fr")

    assert picked["key"] == "VF-CUT"


def test_pick_video_penalises_subbed_and_original_version():
    """English-language penalty markers must fire too."""
    subbed = _video(key="SUB", lang="en", published_at="2024-12-01T00:00:00.000Z")
    subbed["name"] = "Trailer (subbed)"
    original = _video(key="ORIG", lang="en", published_at="2024-12-01T00:00:00.000Z")
    original["name"] = "Trailer (original version)"
    clean = _video(key="CLEAN", lang="en", published_at="2024-01-01T00:00:00.000Z")
    clean["name"] = "Official Trailer"

    picked = _pick_video([subbed, original, clean], "en")

    assert picked["key"] == "CLEAN"


def test_pick_video_japanese_locale_has_no_boost_but_keeps_penalties():
    """A user on ``ja`` gets no name boost — the unknown language falls
    back to Trailer/official/date — but VOSTFR / sous-titré still lose."""
    sub = _video(key="JA-SUB", lang="ja", published_at="2024-12-01T00:00:00.000Z")
    sub["name"] = "Trailer (VOSTFR)"
    clean = _video(key="JA-CLEAN", lang="ja", published_at="2023-01-01T00:00:00.000Z")
    clean["name"] = "予告編"

    picked = _pick_video([sub, clean], "ja")

    assert picked["key"] == "JA-CLEAN"


def test_pick_video_penalises_vostfr_against_dubbed_french():
    """A VOSTFR fan-uploaded fr-tagged trailer must lose to a real dub
    even when its publication date is newer."""
    vostfr = _video(
        key="FAN-VOSTFR",
        official=False,
        published_at="2024-12-01T00:00:00.000Z",
    )
    vostfr["name"] = "Trailer VOSTFR"
    real_vf = _video(
        key="OFFICIAL-VF",
        published_at="2024-01-01T00:00:00.000Z",
    )
    real_vf["name"] = "Bande-annonce officielle"

    picked = _pick_video([vostfr, real_vf], "fr")

    assert picked["key"] == "OFFICIAL-VF"


def test_rank_videos_returns_full_list_best_first():
    """``_rank_videos`` returns every match, best first — the candidate
    list the fallback player cycles through. ``_pick_video`` is just its
    head."""
    teaser = _video(key="OLD-TEASER", type_="Teaser")
    trailer = _video(key="THE-TRAILER", type_="Trailer")

    ranked = _rank_videos([teaser, trailer], "fr")

    assert [r["key"] for r in ranked] == ["THE-TRAILER", "OLD-TEASER"]
    assert _pick_video([teaser, trailer], "fr")["key"] == ranked[0]["key"]


def test_rank_videos_drops_non_youtube_vimeo_and_wrong_type():
    fb = _video(key="FB", site="Facebook")
    clip = _video(key="CLIP", type_="Clip")
    yt = _video(key="YT")

    ranked = _rank_videos([fb, clip, yt], "fr")

    assert [r["key"] for r in ranked] == ["YT"]
