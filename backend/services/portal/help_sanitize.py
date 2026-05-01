"""HTML sanitiser + slug helpers for the Help Center.

The Tiptap WYSIWYG editor on the frontend produces rich HTML (rich text
formatting, tables, links, inline colours / sizes, lists). We pass every
admin-edited blob through ``sanitize_html`` *before persistence* so that
stored content can be safely rendered with ``v-html`` and is permanently
free of script / style / event-handler payloads. A defensive
``DOMPurify`` pass on the client is still cheap insurance, but the
canonical safety boundary lives here.

Slug helpers live alongside because both concerns are pure-string
utilities reused across the service and the seed.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

import bleach
from bleach.css_sanitizer import CSSSanitizer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.help import HelpArticle


# ─────────────────────────── Sanitiser whitelist ───────────────────────────

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

# Tiptap inline styles we keep: colour, background-color, font-size, text
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
    """Return ``existing`` augmented with the missing required tokens.

    Token order is preserved; case-insensitive duplicates are not
    re-added.
    """
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
        # No rel attribute yet — inject one before the closing bracket.
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


# ─────────────────────────── Slug helpers ───────────────────────────

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(title: str, fallback: str = "article") -> str:
    if not title:
        return fallback
    norm = unicodedata.normalize("NFKD", title)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_RE.sub("-", ascii_only).strip("-")
    return slug or fallback


async def _slug_exists(db: AsyncSession, slug: str,
                       exclude_id: Optional[int] = None) -> bool:
    stmt = select(HelpArticle.id).where(HelpArticle.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(HelpArticle.id != exclude_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def resolve_unique_slug(db: AsyncSession, base: str,
                              exclude_id: Optional[int] = None) -> str:
    candidate = slugify(base)
    if not await _slug_exists(db, candidate, exclude_id=exclude_id):
        return candidate
    for n in range(2, 10000):
        suffixed = f"{candidate}-{n}"
        if not await _slug_exists(db, suffixed, exclude_id=exclude_id):
            return suffixed
    raise RuntimeError("could not resolve unique help slug")
