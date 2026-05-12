"""Anonymous display-name helper — privacy boundary for user-facing surfaces."""
import pytest

from services.portal._display_name import (
    parse_accept_language,
    resolve_display_name,
    stable_user_tag,
)


def test_stable_user_tag_returns_4_digit_string():
    tag = stable_user_tag(42)
    assert isinstance(tag, str)
    assert len(tag) == 4
    assert tag.isdigit()


def test_stable_user_tag_is_deterministic():
    assert stable_user_tag(42) == stable_user_tag(42)


def test_stable_user_tag_distinguishes_neighbours():
    assert stable_user_tag(42) != stable_user_tag(43)


def test_resolve_returns_provided_pseudo_fr():
    assert resolve_display_name("Alice", 1, "fr") == "Alice"


def test_resolve_returns_provided_pseudo_strips_whitespace():
    assert resolve_display_name("  Alice  ", 1, "fr") == "Alice"


def test_resolve_returns_fr_alias_when_username_missing():
    out = resolve_display_name(None, 1, "fr")
    assert out.startswith("Utilisateur ")
    assert out.split(" ")[-1] == stable_user_tag(1)


def test_resolve_returns_en_alias_for_en_us_locale():
    out = resolve_display_name(None, 1, "en-US")
    assert out.startswith("User ")
    assert out.split(" ")[-1] == stable_user_tag(1)


def test_resolve_empty_string_treated_as_missing():
    out = resolve_display_name("", 1, "fr")
    assert out.startswith("Utilisateur ")


def test_resolve_whitespace_only_treated_as_missing():
    out = resolve_display_name("   ", 1, "fr")
    assert out.startswith("Utilisateur ")


def test_parse_accept_language_picks_en_when_first():
    assert parse_accept_language("en-US,en;q=0.9,fr;q=0.8") == "en"


def test_parse_accept_language_defaults_to_fr_when_none():
    assert parse_accept_language(None) == "fr"


def test_parse_accept_language_defaults_to_fr_when_empty():
    assert parse_accept_language("") == "fr"


def test_parse_accept_language_returns_fr_when_no_english():
    assert parse_accept_language("fr-FR,fr;q=0.9,de;q=0.8") == "fr"


@pytest.mark.parametrize("uid", [1, 17, 42, 99, 1024, 99999])
def test_stable_user_tag_always_four_digits(uid):
    assert len(stable_user_tag(uid)) == 4
