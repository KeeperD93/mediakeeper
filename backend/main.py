"""Mediakeeper FastAPI entry point — logging, middleware, routers, frontend."""
import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse as _JSONResponse

# Models — required for Base.metadata.create_all
from models.portal.achievement import Achievement, UserAchievement  # noqa: F401
from models.portal.search_document import PortalSearchDocument  # noqa: F401
from models.portal.xp_boost import XpBoostEvent  # noqa: F401
from models.portal.xp_ledger import XpLedger  # noqa: F401
from models.duplicate_cleanup import DoublonCleanup  # noqa: F401
from models.healthcheck import HealthCheckResult  # noqa: F401
from models.ignored_duplicate import IgnoredDoublon  # noqa: F401
from models.notification_channels import NotificationChannel  # noqa: F401
from models.notification_log import NotificationLog  # noqa: F401
from models.playback_stats import PlaybackSession  # noqa: F401
from models.scheduler_task import SchedulerTask  # noqa: F401
from models.security import SecurityAttempt, SecurityBlock  # noqa: F401
from models.seen_alert import SeenAlert  # noqa: F401
from models.subtitle_history import SubtitleDownload  # noqa: F401
from models.subtitle_profile import SubtitleProfile  # noqa: F401
from models.user_preferences import UserPreference  # noqa: F401
from models.watchlist_scans import WatchlistScan  # noqa: F401

from api.alerts import router as alerts_router
from api.auth import router as auth_router
from api.backup import router as backup_router
from api.changelog import APP_VERSION, router as changelog_router
from api.core_routes import register_health_route, router as core_router
from api.csp_report import router as csp_report_router
from api.portal import router as portal_router
from api.portal_changelog import router as portal_changelog_router
from api.duplicates import router as duplicates_router
from api.healthcheck import router as healthcheck_router
from api.logs import router as logs_router
from api.media import router as media_router
from api.notifications import router as notifications_router
from api.onboarding import router as onboarding_router
from api.portal_admin_requests import router as portal_admin_requests_router
from api.portal_admin_users import router as portal_admin_users_router
from api.portal_admin_users_actions import router as portal_admin_users_actions_router
from api.portal_admin_users_emby import router as portal_admin_users_emby_router
from api.portal_admin_users_feed import router as portal_admin_users_feed_router
from api.scheduler import router as scheduler_router
from api.security import router as security_router
from api.settings import router as settings_router
from api.stats import router as stats_router
from api.subtitles import router as subtitles_router
from api.watchlist import router as watchlist_router
from core.app_spa import register_spa
from core.app_startup import is_db_ready, lifespan, setup_logging
from core.csrf_middleware import CsrfMiddleware
from core.log_redaction import safe_request_url
from core.proxy import ProxyHeadersMiddleware
from core.rate_limit import limiter
from core.security_headers import SecurityHeadersMiddleware

setup_logging()
logger = logging.getLogger("mediakeeper")

app = FastAPI(title="Mediakeeper API", version=APP_VERSION, lifespan=lifespan)


class _StartupMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not is_db_ready() and request.url.path.startswith("/api/") and request.url.path != "/api/health":
            return _JSONResponse(
                status_code=503,
                content={"detail": "Service starting up, please wait..."},
            )
        return await call_next(request)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(_StartupMiddleware)
app.add_middleware(CsrfMiddleware)
# Slowapi sits between CSRF and SecurityHeaders so 429 responses still
# carry the security headers (defence-in-depth on every response) while
# the rate-limit kicks in before the inner application work runs.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

MK_DEBUG = os.getenv("MK_DEBUG", "false").lower() in ("true", "1", "yes")

if MK_DEBUG:
    _debug_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[_debug_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    _cors_origin = os.getenv("FRONTEND_ORIGIN", "")
    if _cors_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[_cors_origin],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )

# Outermost: rewrite scope before any other middleware reads request.client
# or request.url.scheme. Stays a no-op when TRUSTED_PROXIES is empty.
app.add_middleware(ProxyHeadersMiddleware)

app.include_router(auth_router)
app.include_router(media_router)
app.include_router(settings_router)
app.include_router(alerts_router)
app.include_router(logs_router)
app.include_router(duplicates_router)
app.include_router(notifications_router)
app.include_router(watchlist_router)
app.include_router(stats_router)
app.include_router(scheduler_router)
app.include_router(onboarding_router)
app.include_router(backup_router)
app.include_router(changelog_router)
app.include_router(healthcheck_router)
app.include_router(subtitles_router)
app.include_router(portal_router)
app.include_router(portal_changelog_router)
app.include_router(portal_admin_requests_router)
app.include_router(portal_admin_users_router)
app.include_router(portal_admin_users_actions_router)
app.include_router(portal_admin_users_emby_router)
app.include_router(portal_admin_users_feed_router)
app.include_router(security_router)
app.include_router(csp_report_router)
app.include_router(core_router)

register_health_route(app, APP_VERSION, is_db_ready)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Capture unhandled exceptions and return a clean JSON response.

    The URL we log is stripped of its query string via
    :func:`safe_request_url` so an unhandled error never echoes
    ``?token=...`` or any other secret-bearing parameter to disk. The
    full URL stays accessible to local developers via the ``request``
    object — production logs only see ``scheme://host/path``.
    """
    logger.error(
        "Unhandled error on %s %s: %s",
        request.method, safe_request_url(request), exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Must be registered last: the SPA fallback captures all non-API routes.
register_spa(app)
