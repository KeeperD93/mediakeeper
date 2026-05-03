"""URL scheme/host whitelist helper used to refuse dangerous URLs at the
edge of any persistence boundary.

The portal stores a few user-supplied URL fields (``user_list_items.poster_url``
today, possibly more in the future). Pydantic ``HttpUrl`` would reject too
many legitimately-malformed-but-safe inputs and would force every caller
to handle validation errors, so we use a small permissive helper that
returns ``None`` on bad input. Callers persist ``None`` and the rendering
layer falls back to the placeholder.

Mirrors ``frontend/src/utils/safeUrl.js`` semantics: only HTTPS schemes
are accepted and an optional host whitelist matches the CSP ``img-src``
sources to avoid surprising regressions.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional
from urllib.parse import urlparse


_BLOCKED_SCHEMES = frozenset({"javascript", "data", "vbscript", "file", "about"})
_DEFAULT_SCHEMES = frozenset({"https"})

# Tabs and newlines hidden inside a URL would let ``\tjavascript:`` slip
# past a naive ``startswith("http")`` check. ``urlparse`` itself ignores
# whitespace, but we strip first so we can also reject bare control
# characters defensively.
_WHITESPACE_RE = re.compile(r"\s+")


def safe_url(
    raw: Optional[str],
    *,
    schemes: Iterable[str] = _DEFAULT_SCHEMES,
    allowed_hosts: Optional[Iterable[str]] = None,
) -> Optional[str]:
    """Return ``raw`` when it parses as a safe URL, else ``None``.

    - ``schemes``: lowercase scheme names accepted (default: ``https``).
    - ``allowed_hosts``: when provided, the URL host (lowercased, no
      port) must match exactly one of these. ``None`` disables the
      host check.
    - ``javascript:``, ``data:``, ``vbscript:``, ``file:``, ``about:``
      are always rejected, even when included in ``schemes``.
    - Empty / non-string / whitespace-only inputs return ``None``.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        return None

    cleaned = _WHITESPACE_RE.sub("", raw).strip()
    if not cleaned:
        return None

    try:
        parsed = urlparse(cleaned)
    except ValueError:
        return None

    scheme = (parsed.scheme or "").lower()
    if not scheme:
        return None
    if scheme in _BLOCKED_SCHEMES:
        return None

    accepted = {s.lower() for s in schemes}
    if scheme not in accepted:
        return None

    host = (parsed.hostname or "").lower()
    if not host:
        return None

    if allowed_hosts is not None:
        whitelist = {h.lower() for h in allowed_hosts}
        if host not in whitelist:
            return None

    return cleaned
