"""Unit contract for the unified request-locale resolution + TMDB mapping.

These are the P1 foundation primitives: the viewer locale comes from the
``X-MK-Locale`` app header (Accept-Language / default as fallbacks), and
``tmdb_language`` turns a 2-letter locale into a TMDB ``xx-YY`` code in a way
that scales to any language without per-call hardcoding.
"""
import pytest

from core.i18n import DEFAULT_LOCALE, normalize_locale, resolve_locale
from services.tmdb import LANGUAGE, tmdb_language


@pytest.mark.parametrize("raw,expected", [
    ("fr", "fr"), ("EN", "en"), ("fr-FR", "fr"), ("pt_BR", "pt"),
    ("  ja  ", "ja"), ("", None), (None, None), ("x", None), ("123", None),
])
def test_normalize_locale(raw, expected):
    assert normalize_locale(raw) == expected


def test_resolve_locale_prefers_app_header():
    # X-MK-Locale wins over the browser Accept-Language.
    assert resolve_locale("en", "fr-FR,fr;q=0.9") == "en"


def test_resolve_locale_falls_back_to_accept_language():
    assert resolve_locale(None, "ja-JP,ja;q=0.9,en;q=0.5") == "ja"


def test_resolve_locale_defaults_when_nothing():
    assert resolve_locale(None, None) == DEFAULT_LOCALE
    assert resolve_locale("", "  ") == DEFAULT_LOCALE


@pytest.mark.parametrize("locale,expected", [
    ("fr", "fr-FR"), ("en", "en-US"), ("ja", "ja-JP"),
    ("de", "de-DE"), ("ru", "ru-RU"), ("pt", "pt-BR"), ("EN", "en-US"),
])
def test_tmdb_language_known(locale, expected):
    assert tmdb_language(locale) == expected


def test_tmdb_language_unknown_uses_xx_fallback():
    # A language without a region entry still yields a valid xx-XX tag.
    assert tmdb_language("sv") == "sv-SV"


def test_tmdb_language_blank_uses_default():
    assert tmdb_language(None) == LANGUAGE
    assert tmdb_language("") == LANGUAGE
    assert tmdb_language("123") == LANGUAGE
