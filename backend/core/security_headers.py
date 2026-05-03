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


CSP_DIRECTIVES = "; ".join([
    "default-src 'self'",
    # ``'unsafe-eval'`` is required by vue-i18n's runtime template
    # compiler (``new Function()``). ``https://www.youtube.com`` is the
    # origin of the IFrame API loader (``/iframe_api``); the embedded
    # iframes themselves still target ``youtube-nocookie.com`` (see
    # ``frame-src`` below) so cookies stay disabled. See module
    # docstring for the ``'unsafe-eval'`` removal plan.
    "script-src 'self' 'unsafe-eval' https://www.youtube.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https://image.tmdb.org https://i.imgur.com",
    "connect-src 'self'",
    # Trailers embed YouTube and Vimeo players; without an explicit
    # ``frame-src`` the ``default-src 'self'`` fallback would block them.
    "frame-src 'self' https://www.youtube-nocookie.com https://player.vimeo.com",
    # Defence in depth: MediaKeeper never renders ``<object>`` / ``<embed>``.
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
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
