"""Security response headers middleware.

Emits the standard defensive headers on every HTTP response:
  - ``Content-Security-Policy``: simplified policy for a SPA standalone
    deployment (no per-request nonce — the SPA is served as a static
    bundle by ``core.app_spa``). Allows Google Fonts (preconnect already
    declared in ``frontend/index.html``), TMDB poster CDN, Imgur uploads.

    ``script-src`` includes ``'unsafe-eval'``: vue-i18n compiles its
    message templates at runtime via ``new Function()``, which a strict
    ``script-src 'self'`` rejects with ``EvalError``. The eval surface is
    bounded to translation strings shipped in our own bundle, not to
    arbitrary user input. Tracked as tech debt — switch vue-i18n to
    pre-compiled messages (``@intlify/unplugin-vue-i18n``) and drop
    ``'unsafe-eval'`` in a follow-up batch.

    ``frame-src`` whitelists the YouTube and Vimeo embed origins so the
    portal trailer player keeps working under enforce mode; ``object-src``
    is locked to ``'none'`` because MediaKeeper never embeds plugins.
  - ``Strict-Transport-Security``: emitted only when the request is
    confirmed HTTPS (after ``ProxyHeadersMiddleware`` rewrites the scope
    based on a trusted proxy).
  - ``X-Frame-Options: DENY``: MediaKeeper is never iframed.
  - ``X-Content-Type-Options: nosniff``: blocks legacy MIME sniffing.
  - ``Referrer-Policy: strict-origin-when-cross-origin``: OWASP default.
  - ``Permissions-Policy``: disables sensor APIs MediaKeeper does not use.
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from core.proxy import is_request_secure


CSP_REPORT_PATH = "/api/csp-violation-report"

# Each whitelisted third-party host carries a one-line traceability
# comment so a future audit can confirm the source is still in use.
# Drop a domain from this list iff the corresponding feature is gone
# AND a grep on the codebase confirms no remaining reference.
CSP_DIRECTIVES = "; ".join([
    "default-src 'self'",
    # ``'unsafe-eval'`` is required by vue-i18n's runtime template
    # compiler (``new Function()``). See module docstring for removal
    # plan.
    # https://www.youtube.com — IFrame API loader (/iframe_api); embed
    # iframes themselves target youtube-nocookie.com on frame-src.
    "script-src 'self' 'unsafe-eval' https://www.youtube.com",
    # https://fonts.googleapis.com — Google Fonts CSS preconnect from
    # frontend/index.html.
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    # https://fonts.gstatic.com — woff2 binary served alongside the CSS.
    "font-src 'self' https://fonts.gstatic.com",
    # https://image.tmdb.org — TMDB posters / backdrops.
    # https://i.imgur.com — operator-supplied banner uploads.
    # https://img.youtube.com — YouTube trailer thumbnails (hqdefault.jpg)
    # composed by services.portal.discover_details_enrich.
    # blob: — Emby user avatars proxied via /api/emby/user-image/{id} are
    # fetched as binary and rendered through URL.createObjectURL() in
    # useUserImages.js. Same pattern is used by any Vue component that
    # previews an upload before sending it. blob: URLs are local to the
    # browser tab and never cross-origin.
    "img-src 'self' data: blob: https://image.tmdb.org https://i.imgur.com https://img.youtube.com",
    "connect-src 'self'",
    # https://www.youtube-nocookie.com — privacy-friendly YouTube embed
    # used by the trailer player.
    # https://player.vimeo.com — Vimeo embed used by the same player.
    "frame-src 'self' https://www.youtube-nocookie.com https://player.vimeo.com",
    # Defence in depth: MediaKeeper never renders ``<object>`` / ``<embed>``.
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    # Browsers POST violation reports here. Kept on the legacy
    # ``report-uri`` directive — broader support than ``report-to``
    # across the Chromium / Firefox / Safari matrix as of 2026.
    f"report-uri {CSP_REPORT_PATH}",
])

HSTS_VALUE = "max-age=31536000; includeSubDomains"

PERMISSIONS_POLICY = ", ".join([
    "camera=()",
    "microphone=()",
    "geolocation=()",
    "payment=()",
    "usb=()",
    "accelerometer=()",
    "gyroscope=()",
    "magnetometer=()",
])


def _csp_mode() -> str:
    """Return ``enforce`` (default) or ``report-only``.

    Override via env ``MK_CSP_MODE=report-only`` for transition periods.
    Vite HMR (``MK_DEBUG=true``) disables CSP entirely to keep the dev
    workflow ergonomic.
    """
    if os.getenv("MK_DEBUG", "").strip().lower() in {"true", "1", "yes", "on"}:
        return "off"
    mode = os.getenv("MK_CSP_MODE", "").strip().lower()
    if mode in {"report-only", "report_only"}:
        return "report-only"
    return "enforce"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = response.headers

        csp_mode = _csp_mode()
        if csp_mode == "enforce":
            headers.setdefault("Content-Security-Policy", CSP_DIRECTIVES)
        elif csp_mode == "report-only":
            headers.setdefault("Content-Security-Policy-Report-Only", CSP_DIRECTIVES)

        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)

        if is_request_secure(request):
            headers.setdefault("Strict-Transport-Security", HSTS_VALUE)

        return response
