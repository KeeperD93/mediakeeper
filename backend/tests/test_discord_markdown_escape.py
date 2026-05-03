"""Discord template rendering hardens user/TMDB-sourced values against
markdown injection (a poisoned media title carrying ``[click](evil)`` is
neutered before reaching the webhook payload)."""
from __future__ import annotations

from services.discord._render import (
    PREFORMATTED_VARS, _apply_vars, escape_discord_markdown,
)


def test_escape_discord_markdown_neuters_link_syntax():
    assert escape_discord_markdown("[click](https://evil)") == r"\[click\]\(https://evil\)"


def test_escape_discord_markdown_neuters_bold_italic_strike():
    out = escape_discord_markdown("**ping** _hint_ ~old~")
    assert out == r"\*\*ping\*\* \_hint\_ \~old\~"


def test_escape_discord_markdown_neuters_spoiler_code_quote():
    out = escape_discord_markdown("||spoiler|| `code` > quote")
    assert out == r"\|\|spoiler\|\| \`code\` \> quote"


def test_escape_discord_markdown_handles_backslashes_first():
    """A leading ``\\`` becomes ``\\\\`` so the escape itself is a
    literal in Discord output, not a markdown escape applied to the
    next char."""
    assert escape_discord_markdown("a\\b") == r"a\\b"


def test_apply_vars_escapes_user_supplied_title():
    """Hostile TMDB title is rendered as plain text instead of a link."""
    tmpl = "**<title>**"
    out = _apply_vars(tmpl, {"title": "[click](https://evil)"})
    assert "(https://evil)" not in out
    assert r"\[click\]" in out
    assert r"\(https://evil\)" in out


def test_apply_vars_keeps_preformatted_tmdb_link():
    """The engine-composed ``[Fiche TMDB](url)`` value MUST stay clickable."""
    tmpl = "Voir <tmdb>"
    out = _apply_vars(tmpl, {"tmdb": "[Fiche TMDB](https://www.themoviedb.org/movie/27205)"})
    assert out == "Voir [Fiche TMDB](https://www.themoviedb.org/movie/27205)"


def test_apply_vars_keeps_template_markdown_intact():
    """The template's own ``**bold**`` markup survives — only the
    substituted *values* are escaped."""
    tmpl = "**<title>** (<year>)"
    out = _apply_vars(tmpl, {"title": "Inception", "year": "2010"})
    assert out == "**Inception** (2010)"


def test_apply_vars_handles_empty_value():
    tmpl = "[<title>]"
    out = _apply_vars(tmpl, {"title": ""})
    assert out == "[]"


def test_preformatted_vars_includes_tmdb_and_imgur():
    assert "tmdb" in PREFORMATTED_VARS
    assert "imgur" in PREFORMATTED_VARS
    assert "tmdb_url" in PREFORMATTED_VARS


def test_apply_vars_neuters_username_with_ping_markup():
    """A relayed Discord-style username carrying ``@everyone`` cannot
    actually @-ping (Discord lets the receiver decide which mentions
    parse), but ``**user**`` would still render as bold."""
    tmpl = "Demande de <user>"
    out = _apply_vars(tmpl, {"user": "**alice**"})
    assert out == r"Demande de \*\*alice\*\*"
