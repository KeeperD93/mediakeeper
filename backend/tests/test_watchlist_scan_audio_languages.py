"""Watchlist scan: surface available audio languages on present episodes.

The Suivi/Manquants UI tags every episode marked "present" with the
2-letter codes of the audio tracks Emby reports for that file. The
``MediaStreams`` extraction must:

* keep audio tracks only (subtitles are excluded by UX decision);
* tolerate either ``Language`` or ``LanguageCode`` and either 639-2/B
  (``"fre"``) or 639-2/T (``"fra"``) variants, plus region suffixes;
* skip unknown codes without faking entries (no fantôme tag);
* preserve the file's track order, deduplicate, and cap the list so the
  serialized scan results stay bounded.
"""

from services.watchlist_scanner._emby import _extract_audio_languages


def _audio(lang: str | None, *, key: str = "Language") -> dict:
    return {"Type": "Audio", key: lang} if lang is not None else {"Type": "Audio"}


def test_extract_keeps_known_codes_in_order_and_uppercases():
    streams = [
        _audio("fre"),
        _audio("eng"),
        {"Type": "Subtitle", "Language": "spa"},
    ]

    assert _extract_audio_languages(streams) == ["FR", "EN"]


def test_extract_returns_empty_list_when_no_audio_streams():
    assert _extract_audio_languages([]) == []
    assert _extract_audio_languages(None) == []
    assert _extract_audio_languages([{"Type": "Subtitle", "Language": "fre"}]) == []


def test_extract_skips_unknown_language_codes_without_fantôme_entries():
    streams = [
        _audio("xxx"),
        _audio("eng"),
        _audio(""),
        _audio(None),
    ]

    assert _extract_audio_languages(streams) == ["EN"]


def test_extract_handles_region_suffix_and_iso_639_2_t_variants():
    streams = [
        _audio("fre-FR"),
        _audio("deu"),  # 639-2/T form for German
        _audio("zho-CN"),
    ]

    assert _extract_audio_languages(streams) == ["FR", "DE", "ZH"]


def test_extract_deduplicates_repeated_languages_preserving_first_position():
    streams = [
        _audio("eng"),
        _audio("fre"),
        _audio("eng"),  # second English track (e.g. commentary)
        _audio("FRE"),  # case-insensitive duplicate
    ]

    assert _extract_audio_languages(streams) == ["EN", "FR"]


def test_extract_caps_at_five_distinct_codes_to_keep_json_bounded():
    streams = [
        _audio("eng"),
        _audio("fre"),
        _audio("spa"),
        _audio("ger"),
        _audio("ita"),
        _audio("jpn"),
        _audio("kor"),
    ]

    out = _extract_audio_languages(streams)

    assert out == ["EN", "FR", "ES", "DE", "IT"]
    assert len(out) == 5


def test_extract_falls_back_to_language_code_field_when_language_absent():
    streams = [_audio("fre", key="LanguageCode")]

    assert _extract_audio_languages(streams) == ["FR"]


def test_extract_ignores_non_dict_entries_defensively():
    streams = [None, "fre", _audio("eng"), 42]

    assert _extract_audio_languages(streams) == ["EN"]
