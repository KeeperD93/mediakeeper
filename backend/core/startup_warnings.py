"""Startup configuration warnings.

Pure, side-effect-only logging helpers called once from ``lifespan`` at
boot. Extracted from ``app_startup`` to keep that module focused on the
lifespan orchestration. See ``docs/operations/tls-deployment.md`` for the
mapping between the env var names and the log labels.
"""
import logging
import os

from constants import env_vars
from core.env_flags import env_truthy

logger = logging.getLogger("mediakeeper")


def _warn_if_secure_cookies_unavailable() -> None:
    """Log a single startup warning when production-like settings cannot
    produce ``Secure`` cookies.

    Triggers when all three conditions hold:
      - ``MK_DEBUG`` is unset or false (production-like).
      - ``COOKIE_SECURE`` is not explicitly set (otherwise the operator
        has overridden the auto-detection on purpose).
      - ``TRUSTED_PROXIES`` is empty (so ``X-Forwarded-Proto`` would be
        ignored by ``ProxyHeadersMiddleware``).

    The startup proceeds normally — this is informational only, to
    surface a misconfiguration that would otherwise silently downgrade
    cookie protection in production.
    """
    if env_truthy(env_vars.MK_DEBUG):
        return
    cookie_secure_set = os.getenv(env_vars.COOKIE_SECURE, "").strip() != ""
    if cookie_secure_set:
        return
    trusted_proxies = os.getenv(env_vars.TRUSTED_PROXIES, "").strip()
    if trusted_proxies:
        return
    logger.warning(
        "[startup] COOKIE_SECURE is unset and TRUSTED_PROXIES is empty in "
        "production-like mode. Session cookies will not carry the Secure flag "
        "until the app is reached over HTTPS or a reverse proxy is whitelisted. "
        "If you intend HTTP-only on a trusted LAN, set COOKIE_SECURE=false in "
        "your .env to acknowledge and silence this warning. "
        "See docs/operations/tls-deployment.md."
    )


def _warn_if_frontend_origin_missing_in_proxy_mode() -> None:
    """Log a single startup warning when Mode B (reverse proxy) is set
    up but ``FRONTEND_ORIGIN`` was left empty.

    In Mode B the operator routes the browser traffic through a TLS
    reverse proxy, so cross-origin checks need an explicit allowlist.
    The CSRF middleware tolerates an unset ``FRONTEND_ORIGIN`` by
    auto-deriving the expected Origin from a trusted ``X-Forwarded-Host``,
    but ``CORSMiddleware`` does not — without ``FRONTEND_ORIGIN`` it will
    refuse browser preflights from the public hostname.

    Triggers when all three conditions hold:
      - ``MK_DEBUG`` is unset or false (production-like).
      - ``TRUSTED_PROXIES`` is non-empty (Mode B reverse proxy).
      - ``FRONTEND_ORIGIN`` is empty.
    """
    if env_truthy(env_vars.MK_DEBUG):
        return
    trusted_proxies = os.getenv(env_vars.TRUSTED_PROXIES, "").strip()
    if not trusted_proxies:
        return
    frontend_origin = os.getenv(env_vars.FRONTEND_ORIGIN, "").strip()
    if frontend_origin:
        return
    logger.warning(
        "[startup] FRONTEND_ORIGIN is unset while TRUSTED_PROXIES is configured "
        "(reverse-proxy mode). CORS preflights from the public origin will be "
        "rejected until FRONTEND_ORIGIN is set to the public URL "
        "(e.g. https://your-domain.example.com)."
    )
