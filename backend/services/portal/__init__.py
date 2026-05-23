"""Display normalisers for portal user-supplied strings.

These helpers tidy up raw text before it lands in the database. They
**ARE NOT** an XSS sanitiser: they only strip naked HTML tags and clip
length so the stored payload is clean for plain-text rendering.

The actual XSS boundary lives elsewhere:
- Vue auto-escapes ``{{ }}`` interpolation, which is how every field
  cleaned by these helpers is rendered today.
- :mod:`services.portal.help_sanitize` runs ``bleach`` with a strict
  whitelist for the only HTML field rendered with ``v-html``.

Never feed the output of :func:`strip_tags_and_trim` directly into a
template that uses ``v-html`` — call ``sanitize_html`` instead.
"""
import re

# Linear-time alternative to ``<[^>]+>``: forbidding ``<`` inside the
# character class prevents the engine from backtracking across nested
# unmatched ``<`` repetitions, keeping ``.sub`` in O(n) instead of O(n²).
# Closes CodeQL py/polynomial-redos #142.
# Sémantique préservée sur HTML bien formé (les tags ne contiennent
# jamais ``<``). Sur input mal formé du type ``<foo<bar>``, l'ancien
# pattern strippait toute la sous-chaîne ; le nouveau ne strippe que
# ``<bar>`` et laisse ``<foo`` visible — comportement plus correct
# pour du stockage plain-text.
_HTML_TAG_RE = re.compile(r'<[^<>]*>')


def strip_tags_and_trim(text: str | None, max_len: int = 5000) -> str:
    """Strip naked HTML tags and clamp length for plain-text storage.

    ``text`` accepts ``None`` to match the guard pattern several callers
    already rely on (``strip_tags_and_trim(data.get("description") or "")``
    becomes simply ``strip_tags_and_trim(data.get("description"))``).
    The return type stays ``str`` — falsy input collapses to ``""``.

    NOT an XSS sanitiser — see module docstring. The returned string is
    safe to render through Vue's ``{{ }}`` (auto-escaped) but must NOT
    be passed to any ``v-html`` binding. For HTML payloads that need to
    survive intact, use :mod:`services.portal.help_sanitize`.
    """
    if not text:
        return ""
    clean = _HTML_TAG_RE.sub('', text)
    return clean[:max_len].strip()


# Backwards-compatible alias preserved while existing call-sites are
# migrated. New code should import ``strip_tags_and_trim`` directly so
# the helper's behaviour ("tag-strip only, NOT an XSS sanitiser") is
# obvious from the import name.
sanitize = strip_tags_and_trim
