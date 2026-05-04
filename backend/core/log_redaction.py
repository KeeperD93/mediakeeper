"""Log redaction filter and request-URL helper.

This module covers two complementary concerns:

* :class:`LogRedactor` — a :class:`logging.Filter` attached to every
  root-logger handler so that sensitive values (passwords, tokens,
  bearer headers, JWTs, Discord webhook secrets, MediaKeeper cookies)
  never reach the rotated log file even when an upstream caller
  forgets to mask them.

* :func:`safe_request_url` — a tiny helper for the global FastAPI
  exception handler. It returns the request URL stripped of its query
  string so an unhandled error never echoes ``?token=...`` to disk.

Patterns are intentionally narrow. A phrase such as "the token of
peace" or "Bearer with sword" stays untouched: only key/value pairs
with an explicit ``=``/``:`` separator and bearer headers carrying a
token-shaped blob are rewritten. The cost of being too aggressive is
unreadable logs; the cost of being too narrow is one extra bug to
report — the second is recoverable, the first is not.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

#: Replacement string used everywhere a value is removed.
REDACTED = "[REDACTED]"

# Each entry is ``(compiled pattern, replacement)``. Order matters:
# more specific patterns run first so the generic key/value pass does
# not over-mask their captures.
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Discord webhook URL — keep the public id (operators correlate
    # with the webhook config), drop only the secret token segment.
    (
        re.compile(r"https://discord\.com/api/webhooks/(\d+)/[A-Za-z0-9_\-]+"),
        r"https://discord.com/api/webhooks/\1/" + REDACTED,
    ),
    # Bearer <token>: require a token-shape blob (>= 20 chars of
    # base64url + dot + dash + plus + slash + equals) so conversational
    # English like "Bearer witness" is not mangled.
    (
        re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]{20,}"),
        f"Bearer {REDACTED}",
    ),
    # Standalone JWT (eyJ<header>.<payload>.<sig>) anywhere in the
    # message — covers cases where an exception traceback embeds a
    # JWT outside an Authorization header.
    (
        re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
        REDACTED,
    ),
    # Sensitive key=value / key:value / "key":"value" pairs. The
    # leading ``\b`` rejects fragments like "subtoken=...". The value
    # captures everything up to the next whitespace or terminator
    # character common in URLs / cookies / JSON. The two ``['"]?``
    # slots make the pattern accept both URL-encoded form
    # (``password=foo``) and JSON form (``"password":"foo"``).
    (
        re.compile(
            r"""(?ix)
            \b
            (?P<key>
                password
                | passwd
                | pwd
                | api[_-]?key
                | access[_-]?token
                | token
                | mk[_-]?token
                | mk[_-]?csrf
                | rq[_-]?token
            )
            ['"]?
            \s* [=:] \s*
            ['"]?
            (?P<value>[^\s;&"'<>]+)
            ['"]?
            """
        ),
        # ``\g<key>=`` is the original key spelling in lower/upper as
        # written in the source so the redacted line still reads as
        # ``Password=[REDACTED]`` or ``api_key=[REDACTED]`` depending
        # on the caller.
        r"\g<key>=" + REDACTED,
    ),
)


class LogRedactor(logging.Filter):
    """Logging filter that scrubs sensitive values from every record.

    Operates on the *rendered* message: :meth:`logging.LogRecord.getMessage`
    is computed once with the original args, the result is passed
    through every redaction pattern, and the record's ``msg`` is
    rewritten with ``args`` cleared so downstream handlers do not
    re-interpolate the original values.

    The filter never raises: a malformed format string (which would
    blow up ``getMessage``) falls through unchanged so a formatting
    bug cannot cause silent log loss.
    """

    name = "mediakeeper.log_redactor"

    def __init__(self, patterns: Iterable[tuple[re.Pattern[str], str]] = _PATTERNS):
        super().__init__(self.name)
        self._patterns = tuple(patterns)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            text = record.getMessage()
        except Exception:
            return True
        original = text
        for pattern, replacement in self._patterns:
            text = pattern.sub(replacement, text)
        if text != original:
            record.msg = text
            record.args = None
        return True


def install_log_redactor() -> None:
    """Attach a :class:`LogRedactor` to every root-logger handler.

    Idempotent: calling it twice (e.g. once in the API process and
    once in the worker process) leaves at most one redactor per
    handler. Filters live on the handlers — not on the root logger
    itself — so that records propagated from child loggers are
    redacted on their way out, which a logger-level filter would not
    catch.
    """
    redactor = LogRedactor()
    for handler in logging.getLogger().handlers:
        if any(isinstance(f, LogRedactor) for f in handler.filters):
            continue
        handler.addFilter(redactor)


def safe_request_url(request) -> str:
    """Return ``request.url`` with the query string and fragment dropped.

    ``request`` is expected to expose a Starlette ``URL`` via the
    ``url`` attribute (FastAPI / Starlette ``Request``). When that is
    not the case the function returns an empty string rather than
    raising, so the caller — typically the global exception handler —
    cannot blow up while reporting another error.
    """
    url = getattr(request, "url", None)
    if url is None:
        return ""
    scheme = getattr(url, "scheme", "") or ""
    netloc = getattr(url, "netloc", "") or ""
    path = getattr(url, "path", "") or ""
    if scheme and netloc:
        return f"{scheme}://{netloc}{path}"
    return path
