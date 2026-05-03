"""Discord template rendering hardens user/TMDB-sourced values against
markdown injection (a poisoned media title carrying ``[click](evil)`` is
neutered before reaching the webhook payload)."""
from __future__ import annotations

import pytest

from services.discord._render import (
    PREFORMATTED_VARS, _apply_vars, escape_discord_markdown,
)
from services.discord.payloads import build_discord_payload


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


def test_apply_vars_escapes_non_preformatted_user_value():
    """Non-preformatted variables (free-text fields like ``description``
    or ``comment``) carrying hostile markdown are rendered as plain
    text — the attack collapses into escaped brackets."""
    tmpl = "Reported: <description>"
    out = _apply_vars(tmpl, {"description": "[click](https://evil)"})
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


def test_preformatted_vars_includes_pre_built_title_links():
    """``payloads.build_discord_payload`` wraps the (pre-escaped) media
    name in ``[name](url)`` and stores it in these variables — they
    must skip ``_apply_vars`` escaping or the link breaks."""
    for key in ("titre", "title", "titre_serie", "series_title"):
        assert key in PREFORMATTED_VARS


def test_apply_vars_neuters_username_with_ping_markup():
    """A relayed Discord-style username carrying ``@everyone`` cannot
    actually @-ping (Discord lets the receiver decide which mentions
    parse), but ``**user**`` would still render as bold."""
    tmpl = "Demande de <user>"
    out = _apply_vars(tmpl, {"user": "**alice**"})
    assert out == r"Demande de \*\*alice\*\*"


# ─────────────────────────── Title link rendering (regression coverage) ───────────────────────────


def _movie_item(name: str, tmdb_id: str = "27205") -> dict:
    return {
        "Type": "Movie",
        "Name": name,
        "ProductionYear": 2010,
        "ProviderIds": {"Tmdb": tmdb_id},
    }


def _series_item(name: str, tmdb_id: str = "1396") -> dict:
    return {
        "Type": "Series",
        "Name": name,
        "ProductionYear": 2008,
        "ChildCount": 5,
        "ProviderIds": {"Tmdb": tmdb_id},
    }


def _embed_description(payload: dict) -> str:
    return payload["embeds"][0]["description"]


@pytest.mark.asyncio
async def test_movie_title_renders_as_clickable_link():
    """A normal movie title must arrive on Discord as ``[Name](url)``
    with literal brackets (not backslash-escaped) so the rendered
    embed shows a single clickable link."""
    payload = await build_discord_payload(
        item=_movie_item("Inception"),
        wh_config={"templates": {}, "settings": {}, "lang": "fr"},
        emby_url="", emby_api_key="",
    )
    desc = _embed_description(payload)
    assert "[Inception](https://www.themoviedb.org/movie/27205)" in desc
    # The structural brackets must not have been backslash-escaped.
    assert r"\[Inception\]" not in desc


@pytest.mark.asyncio
async def test_movie_title_with_injected_markdown_is_defanged():
    """A poisoned title carrying ``[click](evil)`` ends up wrapped in
    the engine link with the inner brackets escaped — Discord renders
    a single legitimate link to TMDB whose anchor text is the literal
    hostile string, not a second clickable link to the attacker's URL."""
    payload = await build_discord_payload(
        item=_movie_item("[click](https://evil)"),
        wh_config={"templates": {}, "settings": {}, "lang": "fr"},
        emby_url="", emby_api_key="",
    )
    desc = _embed_description(payload)
    # No raw attack link in the output.
    assert "(https://evil)" not in desc
    # The engine wrapper survives intact.
    assert "](https://www.themoviedb.org/movie/27205)" in desc
    # The attacker's brackets and parens are escaped inside the anchor.
    assert r"\[click\]" in desc
    assert r"\(https://evil\)" in desc


@pytest.mark.asyncio
async def test_series_title_renders_as_clickable_link():
    """Series notifications use ``Name`` as the title — same
    contract as Movie: rendered as ``[Name](url)``."""
    payload = await build_discord_payload(
        item=_series_item("Breaking Bad"),
        wh_config={"templates": {}, "settings": {}, "lang": "fr"},
        emby_url="", emby_api_key="",
    )
    desc = _embed_description(payload)
    assert "[Breaking Bad](https://www.themoviedb.org/tv/1396)" in desc
    assert r"\[Breaking Bad\]" not in desc


@pytest.mark.asyncio
async def test_series_title_with_injected_markdown_is_defanged():
    payload = await build_discord_payload(
        item=_series_item("[evil](https://attacker)"),
        wh_config={"templates": {}, "settings": {}, "lang": "fr"},
        emby_url="", emby_api_key="",
    )
    desc = _embed_description(payload)
    assert "(https://attacker)" not in desc
    assert "](https://www.themoviedb.org/tv/1396)" in desc
    assert r"\[evil\]" in desc
    assert r"\(https://attacker\)" in desc
