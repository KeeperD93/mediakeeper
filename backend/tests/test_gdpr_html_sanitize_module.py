"""Verify the Batch 11B refactor of ``sanitize_html``.

The sanitiser moved from ``services.portal.help_sanitize`` to
``services.portal._html_sanitize`` so the GDPR opt-in surface can
share the exact same Tiptap → bleach pipeline. This file exercises:

* the new canonical import path,
* the legacy re-export from ``help_sanitize`` (kept to avoid a flag
  day on every existing call site),
* idempotence of the migration 040 default privacy texts (FR + EN
  pass through ``sanitize_html`` unchanged),
* a handful of structural drops to cover edge cases new to the GDPR
  use-case (``data-*`` attrs, mismatched protocols).
"""
from services.portal._html_sanitize import sanitize_html as canonical_sanitize
from services.portal.help_sanitize import sanitize_html as legacy_sanitize


# ---------------------------------------------------------------------------
# Re-export parity
# ---------------------------------------------------------------------------


def test_legacy_help_sanitize_reexports_canonical_implementation():
    assert legacy_sanitize is canonical_sanitize


# ---------------------------------------------------------------------------
# Idempotence on the migration 040 preset privacy texts
# ---------------------------------------------------------------------------


_FR_DEFAULT = """\
<h2>Politique de confidentialité</h2>
<p>Cette instance MediaKeeper est hébergée et administrée par <strong>[NOM DE L'ADMINISTRATEUR — à compléter]</strong>.</p>
<h3>Données collectées</h3>
<ul>
  <li>Identifiant et avatar Emby</li>
  <li>Listes de visionnage et demandes de médias</li>
  <li>Messages de chat</li>
</ul>
<h3>Sécurité</h3>
<p>Les données sont stockées sur un serveur opéré par l'administrateur.</p>"""


_EN_DEFAULT = """\
<h2>Privacy policy</h2>
<p>This MediaKeeper instance is hosted and administered by <strong>[ADMINISTRATOR NAME — to be filled in]</strong>.</p>
<h3>Data collected</h3>
<ul>
  <li>Emby identifier and avatar</li>
</ul>"""


def test_fr_default_privacy_text_is_idempotent():
    once = canonical_sanitize(_FR_DEFAULT)
    twice = canonical_sanitize(once)
    assert once == twice
    # The whitelist keeps the structural tags used by the preset.
    for tag in ("<h2>", "<h3>", "<p>", "<strong>", "<ul>", "<li>"):
        assert tag in once


def test_en_default_privacy_text_is_idempotent():
    once = canonical_sanitize(_EN_DEFAULT)
    twice = canonical_sanitize(once)
    assert once == twice
    assert "<h2>" in once
    assert "<strong>" in once


# ---------------------------------------------------------------------------
# Drops new to the GDPR use-case
# ---------------------------------------------------------------------------


def test_drops_data_attribute_on_span():
    out = canonical_sanitize('<span data-evil="x">hi</span>')
    assert "data-evil" not in out
    assert "hi" in out


def test_drops_javascript_protocol_on_link():
    out = canonical_sanitize('<a href="javascript:alert(1)">click</a>')
    assert "javascript:" not in out


def test_keeps_mailto_protocol_for_dpo_contact_links():
    """The privacy text often links to a mailto: contact — make sure
    bleach's protocol whitelist still allows it after the refactor."""
    out = canonical_sanitize('<a href="mailto:dpo@example.org">contact</a>')
    assert 'href="mailto:dpo@example.org"' in out


def test_strips_style_block_with_content():
    """``<style>…</style>`` is stripped wholesale by the pre-pass so
    privacy text rendered with ``v-html`` cannot smuggle CSS that
    overlays the surrounding admin UI."""
    out = canonical_sanitize(
        "<style>body { display: none }</style><p>policy</p>"
    )
    assert "<style" not in out
    assert "display: none" not in out
    assert "<p>policy</p>" in out
