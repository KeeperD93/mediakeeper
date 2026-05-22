"""Generic HTML sanitiser shared by every WYSIWYG-edited surface.

Originally lived inside ``help_sanitize.py`` for the Help Center. The
GDPR opt-in mode needs the exact same pipeline for the admin-edited
privacy texts, so the sanitiser was lifted into its own module. Help
Center continues to import ``sanitize_html`` from ``help_sanitize``
for backward compatibility, but new callers should import from this
module directly.

The sanitiser is the canonical safety boundary between the Tiptap
editor on the frontend and ``v-html`` rendering: every admin-edited
blob passes through here *before persistence* so stored content can
never embed scripts, event handlers, or hostile inline CSS payloads.
A ``DOMPurify`` second pass on the client is still cheap insurance.
"""
from __future__ import annotations

import re

import bleach
from bleach.css_sanitizer import CSSSanitizer


ALLOWED_TAGS = frozenset({
    "p", "br", "hr", "blockquote", "pre", "code",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "u", "s", "mark", "sup", "sub", "small",
    "ul", "ol", "li",
    "a", "abbr", "span", "div",
    "table", "thead", "tbody", "tr", "th", "td",
    "img",
})

ALLOWED_ATTRS = {
    "*": ["class", "id"],
    "a": ["href", "title", "target", "rel"],
    "abbr": ["title"],
    "span": ["style"],
    "div": ["style"],
    "p": ["style"],
    "td": ["colspan", "rowspan", "style"],
    "th": ["colspan", "rowspan", "style", "scope"],
    "img": ["src", "alt", "width", "height", "loading"],
}

# Inline styles we keep: colour, background-color, font-size, text
# alignment. Anything else is dropped by the CSS sanitiser so a hostile
# editor cannot smuggle ``position: fixed`` overlays or
# ``background-image: url(javascript:…)`` payloads.
ALLOWED_CSS_PROPS = ("color", "background-color", "font-size", "text-align")

ALLOWED_PROTOCOLS = frozenset({"http", "https", "mailto"})


def _attr_filter(tag: str, name: str, value: str) -> bool:
    allowed = set(ALLOWED_ATTRS.get("*", [])) | set(ALLOWED_ATTRS.get(tag, []))
    if name not in allowed:
        return False
    if name == "href":
        proto = value.split(":", 1)[0].lower() if ":" in value else ""
        return not proto or proto in ALLOWED_PROTOCOLS
    if name == "target" and value not in ("_blank", "_self"):
        return False
    return True


# Pre-pass strips full ``<script>…</script>`` and ``<style>…</style>``
# blocks (content + tag). Bleach with ``strip=True`` only drops the
# wrapper, leaving raw script text inside the document — visually noisy
# even though it's no longer executable.
_DANGEROUS_BLOCKS_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)

_CSS_SANITIZER = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPS)


# Post-pass: every ``<a target="_blank">`` link is hardened with
# ``rel="noopener noreferrer"`` to defend against tabnabbing — the new
# tab would otherwise inherit a ``window.opener`` reference and could
# rewrite the source document's ``location.href``. Existing rel tokens
# (e.g. ``nofollow``) are kept in their original order; only the missing
# ``noopener`` / ``noreferrer`` values are appended.
_BLANK_TARGET_LINK_RE = re.compile(
    r'<a\b[^>]*\btarget=["\']_blank["\'][^>]*?>',
    re.IGNORECASE,
)
_REL_ATTR_RE = re.compile(
    r'\brel\s*=\s*(["\'])(.*?)\1',
    re.IGNORECASE,
)
_REQUIRED_REL_TOKENS = ("noopener", "noreferrer")


def _merge_rel_tokens(existing: str) -> str:
    tokens = existing.split()
    have = {t.lower() for t in tokens}
    merged = list(tokens)
    for required in _REQUIRED_REL_TOKENS:
        if required not in have:
            merged.append(required)
            have.add(required)
    return " ".join(merged)


def _force_noopener_on_blank_targets(html: str) -> str:
    def _harden(match: re.Match) -> str:
        tag = match.group(0)
        rel_match = _REL_ATTR_RE.search(tag)
        if rel_match is not None:
            quote = rel_match.group(1)
            existing = rel_match.group(2)
            merged = _merge_rel_tokens(existing)
            if merged == existing:
                return tag
            new_rel = f"rel={quote}{merged}{quote}"
            return tag[: rel_match.start()] + new_rel + tag[rel_match.end():]
        if tag.endswith("/>"):
            return f'{tag[:-2].rstrip()} rel="noopener noreferrer" />'
        return f'{tag[:-1].rstrip()} rel="noopener noreferrer">'

    return _BLANK_TARGET_LINK_RE.sub(_harden, html)


def sanitize_html(raw: str) -> str:
    """Drop unsafe tags / attributes / protocols from a WYSIWYG paste.

    Rules: tags outside ``ALLOWED_TAGS`` are stripped; ``<script>`` and
    ``<style>`` blocks are removed *with their content*; attributes go
    through ``_attr_filter``; inline CSS goes through bleach's
    ``CSSSanitizer`` so only the four whitelisted properties survive
    and ``url(...)`` payloads are rejected; only http/https/mailto are
    accepted on ``href``. Finally, every ``<a target="_blank">`` link
    is hardened with ``rel="noopener noreferrer"`` (existing rel tokens
    are preserved and merged with the required ones).
    """
    if not raw:
        return ""
    pre = _DANGEROUS_BLOCKS_RE.sub("", raw)
    cleaned = bleach.clean(
        pre,
        tags=ALLOWED_TAGS,
        attributes=_attr_filter,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_CSS_SANITIZER,
        strip=True,
        strip_comments=True,
    )
    return _force_noopener_on_blank_targets(cleaned)
