"""Anonymous display-name helper — privacy boundary for user-facing surfaces."""
from services.portal._display_name import (
    parse_accept_language,
    resolve_display_name,
)
from services.portal._pseudo_words import generate_pseudo


def test_resolve_returns_provided_pseudo_fr():
    assert resolve_display_name("Alice", 1, "fr") == "Alice"


def test_resolve_returns_provided_pseudo_strips_whitespace():
    assert resolve_display_name("  Alice  ", 1, "fr") == "Alice"


def test_resolve_generates_fr_pseudo_when_username_missing():
    out = resolve_display_name(None, 1, "fr")
    assert out == generate_pseudo(1, "fr")
    assert " " not in out  # hyphen-joined word-word-number, never raw login


def test_resolve_generates_en_pseudo_for_en_us_locale():
    assert resolve_display_name(None, 1, "en-US") == generate_pseudo(1, "en")


def test_resolve_empty_string_treated_as_missing():
    assert resolve_display_name("", 1, "fr") == generate_pseudo(1, "fr")


def test_resolve_whitespace_only_treated_as_missing():
    assert resolve_display_name("   ", 1, "fr") == generate_pseudo(1, "fr")


def test_resolve_admin_label_fr():
    assert resolve_display_name("admin", 1, "fr", is_admin=True) == "Administrateur"


def test_resolve_admin_label_en():
    assert resolve_display_name("admin", 1, "en-US", is_admin=True) == "Administrator"


def test_resolve_admin_label_wins_over_username_and_pseudo():
    assert resolve_display_name("Bob", 99, "fr", is_admin=True) == "Administrateur"


def test_parse_accept_language_picks_en_when_first():
    assert parse_accept_language("en-US,en;q=0.9,fr;q=0.8") == "en"


def test_parse_accept_language_defaults_to_fr_when_none():
    assert parse_accept_language(None) == "fr"


def test_parse_accept_language_defaults_to_fr_when_empty():
    assert parse_accept_language("") == "fr"


def test_parse_accept_language_returns_fr_when_no_english():
    assert parse_accept_language("fr-FR,fr;q=0.9,de;q=0.8") == "fr"
