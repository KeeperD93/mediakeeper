"""Drift guard: every third-party host hardcoded in the frontend must
either be present in ``CSP_DIRECTIVES`` (so the browser can fetch the
resource) or be explicitly allowlisted below as a non-browser-loaded
host (e.g. an ``<a href>`` link to GitHub, an external Terms-of-Use
URL).

Scope: this catches the kind of regression we hit when ``img.youtube.com``
was added to a backend module without updating the CSP — every page
crashed in enforce mode until the entry was wired in. Adding a new
hardcoded URL to a Vue template now fails this test if the host has
not been registered upstream.

Out of scope: dynamic URLs computed at runtime from environment
(``window.location.host``…) and URLs assembled by the backend before
shipping to the browser. Those are caught by the existing CSP
violation report endpoint instead.
"""
from __future__ import annotations

import re
from pathlib import Path

from core.security_headers import CSP_DIRECTIVES


_FRONTEND_ROOT = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
_SCANNED_SUFFIXES = (".vue", ".html", ".ts", ".js")
_SKIPPED_DIR_NAMES = {"__tests__", "node_modules", "dist", ".vite", "coverage"}

# Match http(s) URLs with a hostname containing at least one dot. The
# trailing character class stops at the first whitespace, quote or
# template-literal delimiter so the captured host is always usable.
_URL_PATTERN = re.compile(r"https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")

# Hosts that may legitimately appear in source files without being
# reachable from a CSP directive — typically external links opened in
# a new tab (`<a href target="_blank">`), placeholder strings shown to
# the user, or documentation URLs in code comments.
_NON_BROWSER_LOADED_HOSTS = frozenset({
    # Project home / repo / community links
    "github.com",
    "discord.gg",
    "wiki.mediakeeper.app",
    "mediakeeper.app",
    # Maintainer support / donation link surfaced as an <a> button
    # (window.open with target=_blank, noopener,noreferrer) — never
    # embedded as iframe/img/script in the MediaKeeper document.
    "ko-fi.com",
    # Third-party reference links surfaced to the user as <a href>
    "www.themoviedb.org",
    "www.imdb.com",
    "emby.media",
    "www.opensubtitles.com",
    "www.opensubtitles.org",
    "ffmpeg.org",
    # Discord webhook URL — only used as validation prefix and as form
    # placeholder text, never loaded as an iframe/img/script.
    "discord.com",
    # SVG namespace literal in inline data: URIs.
    "www.w3.org",
    # RFC 5737 / IANA reserved example domains used in unit tests.
    "example.com",
    "example.org",
    "example.net",
    "x.test",
})


def _iter_frontend_files() -> list[Path]:
    files: list[Path] = []
    for path in _FRONTEND_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in _SCANNED_SUFFIXES:
            continue
        if any(part in _SKIPPED_DIR_NAMES for part in path.parts):
            continue
        files.append(path)
    return files


def _collect_hosts_referenced_in_frontend() -> set[str]:
    seen: set[str] = set()
    for file_path in _iter_frontend_files():
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in _URL_PATTERN.finditer(text):
            seen.add(match.group(1).lower())
    return seen


def _hosts_present_in_csp() -> set[str]:
    return {
        match.group(1).lower()
        for match in _URL_PATTERN.finditer(CSP_DIRECTIVES)
    }


def test_no_third_party_host_drifts_outside_csp_or_allowlist():
    referenced = _collect_hosts_referenced_in_frontend()
    csp_hosts = _hosts_present_in_csp()
    allowed = csp_hosts | _NON_BROWSER_LOADED_HOSTS

    drift = sorted(host for host in referenced if host not in allowed)
    assert not drift, (
        "The following hostnames are referenced in the frontend codebase but "
        "are neither covered by CSP_DIRECTIVES nor by the non-browser-loaded "
        "allowlist in this test. Either add them to backend/core/"
        "security_headers.py:CSP_DIRECTIVES (if browser-loaded) or to "
        "_NON_BROWSER_LOADED_HOSTS in this file (if reached only via "
        "<a href> external link). Drift: " + ", ".join(drift)
    )
