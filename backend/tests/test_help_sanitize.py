"""HTML sanitiser tests for the Help Center.

The sanitiser is the security boundary between the WYSIWYG editor and
``v-html`` rendering on the frontend, so each whitelist edge is
exercised: tag drop, event-handler strip, protocol allowlist, inline
style allowlist (only colour/background/size/text-align survive).
"""
from services.portal.help_sanitize import sanitize_html, slugify


def test_strips_script_tag():
    out = sanitize_html("<p>Hello</p><script>alert(1)</script>")
    assert "<script" not in out
    assert "alert" not in out
    assert "Hello" in out


def test_strips_event_handlers():
    out = sanitize_html('<p onclick="alert(1)">x</p>')
    assert "onclick" not in out
    assert "<p>x</p>" in out


def test_drops_javascript_protocol():
    out = sanitize_html('<a href="javascript:alert(1)">click</a>')
    assert "javascript:" not in out
    # Tag may stay but href is stripped.
    assert "click" in out


def test_keeps_https_link_with_target_blank():
    out = sanitize_html('<a href="https://example.com" target="_blank">go</a>')
    assert 'href="https://example.com"' in out
    assert 'target="_blank"' in out


def test_blank_target_without_rel_gets_noopener_noreferrer():
    out = sanitize_html('<a href="https://example.com" target="_blank">go</a>')
    assert 'target="_blank"' in out
    assert 'rel="noopener noreferrer"' in out


def test_blank_target_with_nofollow_keeps_nofollow_and_appends():
    out = sanitize_html(
        '<a href="https://x.com" target="_blank" rel="nofollow">go</a>'
    )
    assert 'rel="nofollow noopener noreferrer"' in out


def test_blank_target_with_complete_rel_is_not_duplicated():
    out = sanitize_html(
        '<a href="https://x.com" target="_blank" rel="noopener noreferrer">go</a>'
    )
    assert out.count("noopener") == 1
    assert out.count("noreferrer") == 1


def test_self_target_is_not_hardened():
    out = sanitize_html('<a href="https://x.com" target="_self">go</a>')
    assert 'target="_self"' in out
    assert "noopener" not in out
    assert "noreferrer" not in out


def test_keeps_allowed_tags():
    raw = (
        "<h2>Titre</h2><p><strong>gras</strong> <em>italique</em> "
        "<u>souligné</u> <mark>surligné</mark></p>"
        "<ul><li>a</li><li>b</li></ul>"
        "<table><tr><th>k</th><td>v</td></tr></table>"
    )
    out = sanitize_html(raw)
    for needle in ("<h2>", "<strong>", "<em>", "<u>", "<mark>", "<ul>",
                   "<li>", "<table>", "<th>", "<td>"):
        assert needle in out


def test_keeps_allowed_inline_styles():
    raw = '<span style="color: #ff0000; font-size: 1.2em">x</span>'
    out = sanitize_html(raw)
    assert "color" in out
    assert "font-size" in out


def test_drops_disallowed_inline_styles():
    raw = '<span style="position: fixed; color: red; left: 0">x</span>'
    out = sanitize_html(raw)
    assert "position" not in out
    assert "left" not in out
    assert "color" in out  # whitelisted, kept


def test_drops_url_in_styles():
    # Bleach's CSS sanitiser rewrites unsafe ``url(...)`` payloads to a
    # ``[bad url]`` placeholder — the ``javascript:`` scheme and the
    # alert call must both be gone, even if the literal ``url(`` token
    # may remain as a now-pointless CSS reference.
    raw = '<span style="background-color: url(javascript:alert(1))">x</span>'
    out = sanitize_html(raw)
    assert "javascript:" not in out
    assert "alert" not in out


def test_empty_input_returns_empty():
    assert sanitize_html("") == ""
    assert sanitize_html(None) == ""


def test_slugify_basic():
    assert slugify("Comment faire une demande ?") == "comment-faire-une-demande"


def test_slugify_strips_accents_and_punctuation():
    assert slugify("À l'aïe & co !") == "a-l-aie-co"


def test_slugify_falls_back_for_empty():
    assert slugify("", fallback="x") == "x"
    assert slugify("???", fallback="x") == "x"
