"""Mediakeeper application initialization: DB, logs, watchlist cache, lifespan."""
import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager

import models  # noqa: F401  # Ensure every SQLAlchemy model is registered on Base.metadata
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from constants import env_vars
from core.database import engine
from core.env_flags import env_truthy
from core.http_client import close_clients, init_clients
from core.log_redaction import install_log_redactor
from core.logging_config import JSONFormatter
from core.security import hash_password
from core.startup_db import (
    _emit_bootstrap_admin_credentials,
    _schema_mode,
    _validate_registered_schema,
)
from core.startup_warnings import (
    _warn_if_frontend_origin_missing_in_proxy_mode,
    _warn_if_secure_cookies_unavailable,
)
from models.base import Base
from models.user import User
from services.background_tasks import BackgroundTaskManager
from services.logs import LOG_DIR, MEDIAKEEPER_LOG, ensure_log_dir, rotate_logs_if_needed
from services.settings import encrypt_legacy_sensitive_values, get_setting

logger = logging.getLogger("mediakeeper")

# Username of the bootstrap admin seeded by init_db on first run.
_BOOTSTRAP_ADMIN_USERNAME = "admin"

# Process role: "web" serves the API, "worker" runs background jobs, "combined"
# (the default) does both. Only combined/worker drive the in-process task manager.
_ROLE_COMBINED = "combined"
_ROLE_WORKER = "worker"
_DEFAULT_PROCESS_ROLE = _ROLE_COMBINED
_BACKGROUND_TASK_ROLES = frozenset({_ROLE_COMBINED, _ROLE_WORKER})

_PROCESS_ROLE = os.getenv(env_vars.MK_PROCESS_ROLE, _DEFAULT_PROCESS_ROLE).strip().lower() or _DEFAULT_PROCESS_ROLE
_db_ready = False
_file_handler: logging.FileHandler | None = None


def is_db_ready() -> bool:
    return _db_ready


def apply_debug_level(enabled: bool) -> None:
    """Move BOTH the ``mediakeeper`` logger and the file handler to the debug
    level together. Setting only the logger level leaves the file handler
    filtering DEBUG records out of the log file — the runtime-toggle bug."""
    level = logging.DEBUG if enabled else logging.INFO
    logging.getLogger("mediakeeper").setLevel(level)
    if _file_handler is not None:
        _file_handler.setLevel(level)


def setup_logging() -> None:
    """Configure logging handlers (console + file) based on MK_DEBUG."""
    global _file_handler
    mk_debug = env_truthy(env_vars.MK_DEBUG)
    initial_level = logging.DEBUG if mk_debug else logging.INFO

    ensure_log_dir()

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(level=initial_level, format=log_format, datefmt=log_datefmt)

    try:
        _file_handler = logging.FileHandler(str(LOG_DIR / MEDIAKEEPER_LOG), encoding="utf-8")
    except OSError as exc:
        _file_handler = None
        logging.getLogger("mediakeeper").warning(
            "Unable to open log file %s: %s. Falling back to console-only.",
            LOG_DIR / MEDIAKEEPER_LOG,
            exc,
        )
    else:
        if mk_debug:
            _file_handler.setFormatter(logging.Formatter(log_format, datefmt=log_datefmt))
        else:
            _file_handler.setFormatter(JSONFormatter())
        _file_handler.setLevel(initial_level)
        logging.getLogger().addHandler(_file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Attach the redactor last so every handler registered above is
    # covered. Idempotent — safe under repeated setup_logging() calls
    # from API + worker entrypoints.
    install_log_redactor()


async def init_db():
    """Validate/initialize the schema, then create the bootstrap admin account if needed."""
    global _db_ready
    schema_mode = _schema_mode()
    for attempt in range(30):
        try:
            async with engine.begin() as conn:
                if schema_mode == "create_all":
                    await conn.run_sync(Base.metadata.create_all)
                else:
                    await conn.run_sync(_validate_registered_schema)
            break
        except Exception as e:
            logger.warning("[init_db] DB not ready (attempt %s/30): %s", attempt + 1, e)
            await asyncio.sleep(1)
    else:
        logger.error("[init_db] DB unreachable after 30s — aborting")
        return

    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(User).where(User.username == _BOOTSTRAP_ADMIN_USERNAME)
            )
            existing = result.scalar_one_or_none()
            if not existing:
                initial_password = secrets.token_urlsafe(32)
                admin = User(
                    username             = _BOOTSTRAP_ADMIN_USERNAME,
                    hashed_password      = hash_password(initial_password),
                    is_active            = True,
                    must_change_password = True,
                )
                session.add(admin)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                else:
                    _emit_bootstrap_admin_credentials(_BOOTSTRAP_ADMIN_USERNAME, initial_password)
    except Exception as exc:
        logger.error(
            "[init_db] Schema validated but unusable at runtime: %s. "
            "Apply Alembic migrations before restarting.",
            exc,
        )
        return
    _db_ready = True
    logger.info("[init_db] Database ready (schema_mode=%s).", schema_mode)


async def apply_runtime_settings() -> None:
    """Load runtime settings required by the web app and the worker."""
    async with AsyncSession(engine) as session:
        migrated = await encrypt_legacy_sensitive_values(session)
        if migrated["settings"] or migrated["notification_channels"]:
            logger.info("[startup] Encrypted legacy cleartext secrets: %s", migrated)
        debug_mode = await get_setting(session, "logs.debug_mode")
        apply_debug_level(debug_mode == "true")
        if debug_mode == "true":
            logger.info("Debug mode enabled from configuration")

    async with AsyncSession(engine) as session:
        from services.media_manager import load_categories
        await load_categories(session)


async def prime_watchlist_cache() -> None:
    from services.watchlist_scanner import ensure_cache_loaded
    try:
        async with AsyncSession(engine) as session:
            await ensure_cache_loaded(session)
        logger.info("Watchlist cache loaded from DB")
    except Exception as e:
        logger.warning("Watchlist cache unavailable at startup: %s", e)


def _log_deployment_mode() -> None:
    """Print a one-shot diagnostic summary so an operator opening the
    container logs at boot can sanity-check the deployment mode.

    The line surfaces three env vars: ``TRUSTED_PROXIES`` (Mode A vs
    Mode B), ``FRONTEND_ORIGIN`` (chat WS allowlist) and the
    cookie-hardening flag. All three are read fresh from the
    environment at startup so a config reload via container restart
    shows up here.

    See ``docs/operations/tls-deployment.md`` for the mapping between
    env var names and the log labels.
    """
    trusted = os.getenv(env_vars.TRUSTED_PROXIES, "").strip()
    frontend = os.getenv(env_vars.FRONTEND_ORIGIN, "").strip()
    cookie_https = os.getenv(env_vars.COOKIE_SECURE, "").strip()

    mode = "B (reverse proxy)" if trusted else "A (direct LAN)"
    frontend_label = frontend if frontend else "auto-derived"
    cookie_https_label = cookie_https if cookie_https else "auto"

    logger.info(
        "[startup] deployment mode=%s | TRUSTED_PROXIES=%s | "
        "FRONTEND_ORIGIN=%s | COOKIE_HTTPS_FLAG=%s",
        mode,
        trusted or "(empty)",
        frontend_label,
        cookie_https_label,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown."""
    from services.subtitle_sources.opensubtitles_source import OpenSubtitlesSource
    from services.subtitle_sources.registry import register_source

    background_manager: BackgroundTaskManager | None = None

    _log_deployment_mode()
    _warn_if_secure_cookies_unavailable()
    _warn_if_frontend_origin_missing_in_proxy_mode()

    await init_clients()
    await init_db()

    if not is_db_ready():
        logger.error(
            "[STARTUP] DB not ready after schema validation. "
            "API routes will stay in 503 until fixed."
        )
        yield
        await close_clients()
        await engine.dispose()
        return

    register_source(OpenSubtitlesSource())

    rotate_logs_if_needed()
    await apply_runtime_settings()
    await prime_watchlist_cache()

    try:
        from core.database import AsyncSessionLocal
        from services.portal.achievements import seed_achievements
        logger.info("[STARTUP] Seeding achievements...")
        async with AsyncSessionLocal() as seed_db:
            await seed_achievements(seed_db)
        logger.info("[STARTUP] Achievement seed done")
    except Exception:
        logger.exception("[STARTUP] Achievement seed FAILED")

    try:
        from core.database import AsyncSessionLocal
        from services.portal.help import ensure_seed as ensure_help_seed
        logger.info("[STARTUP] Seeding help articles...")
        async with AsyncSessionLocal() as seed_db:
            created = await ensure_help_seed(seed_db)
        logger.info("[STARTUP] Help seed done (created=%s)", created)
    except Exception:
        logger.exception("[STARTUP] Help seed FAILED")

    # Prime the image-cache enable flag so ``_normalize`` doesn't
    # silently default to OFF for the first 30 s while the cached
    # snapshot is still empty.
    try:
        from core.database import AsyncSessionLocal
        from services.portal.image_cache import refresh_enabled_flag
        async with AsyncSessionLocal() as seed_db:
            await refresh_enabled_flag(seed_db, force=True)
    except Exception:
        logger.exception("[STARTUP] Image cache flag prime FAILED")

    # Apply the DNS cache toggle right at startup so every outbound
    # call (TMDB, OpenSubtitles, Emby, …) inherits the resolver wrap
    # from the first request onwards.
    try:
        from core.database import AsyncSessionLocal
        from services.portal.dns_cache import refresh_from_settings as dns_refresh
        async with AsyncSessionLocal() as seed_db:
            await dns_refresh(seed_db)
    except Exception:
        logger.exception("[STARTUP] DNS cache toggle apply FAILED")

    if _PROCESS_ROLE in _BACKGROUND_TASK_ROLES:
        background_manager = BackgroundTaskManager(engine)
        await background_manager.start()

    yield

    if background_manager is not None:
        await background_manager.stop()
    await close_clients()
    await engine.dispose()
