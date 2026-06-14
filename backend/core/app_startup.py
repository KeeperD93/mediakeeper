"""Mediakeeper application initialization: DB, logs, watchlist cache, lifespan."""
import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager

import models  # noqa: F401  # Ensure every SQLAlchemy model is registered on Base.metadata
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from constants import env_vars
from core.database import DATABASE_URL, engine
from core.env_flags import env_truthy
from core.http_client import close_clients, init_clients
from core.log_redaction import install_log_redactor
from core.logging_config import JSONFormatter
from core.security import hash_password
from models.base import Base
from models.user import User
from services.background_tasks import BackgroundTaskManager
from services.logs import LOG_DIR, MEDIAKEEPER_LOG, ensure_log_dir, rotate_logs_if_needed
from services.settings import encrypt_legacy_sensitive_values, get_setting

logger = logging.getLogger("mediakeeper")

_PROCESS_ROLE = os.getenv(env_vars.MK_PROCESS_ROLE, "combined").strip().lower() or "combined"
_db_ready = False
_file_handler: logging.FileHandler | None = None


def is_db_ready() -> bool:
    return _db_ready


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


def _schema_mode() -> str:
    """
    Determine how startup handles the DB schema.

    - sqlite test/dev DBs keep ``create_all`` for convenience.
    - Postgres defaults to ``validate`` so runtime no longer masks
      missing Alembic migrations by creating tables on the fly.
    - ``MK_DB_SCHEMA_MODE=create_all`` keeps the old bootstrap
      behaviour explicitly when needed.
    """
    raw = (os.getenv(env_vars.MK_DB_SCHEMA_MODE, "auto").strip().lower() or "auto")
    if raw in {"create_all", "validate"}:
        return raw
    return "create_all" if DATABASE_URL.startswith("sqlite") else "validate"


def _validate_registered_schema(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())
    missing = sorted(expected_tables - existing_tables)
    if missing:
        preview = ", ".join(missing[:8])
        if len(missing) > 8:
            preview += ", ..."
        raise RuntimeError(
            "Incomplete DB schema. Missing tables: "
            f"{preview}. Apply Alembic migrations or set MK_DB_SCHEMA_MODE=create_all."
        )


def _emit_bootstrap_admin_credentials(username: str, password: str) -> None:
    """
    Display initial credentials on the console output only
    to avoid persisting them in log files.
    """
    lines = [
        "=" * 60,
        "  ADMIN ACCOUNT CREATED",
        f"  Username: {username}",
        f"  Password: {password}",
        "  You MUST change this password on first login.",
        "  CAPTURE THIS NOW — it is not written to /data and",
        "  cannot be recovered from disk later.",
        "  Lost it? See docs/operations/admin-recovery.md",
        "  (run scripts/reset_admin from a host docker exec).",
        "=" * 60,
    ]
    emitted = False
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            stream = getattr(handler, "stream", None)
            if not stream:
                continue
            for line in lines:
                stream.write(f"{line}\n")
            stream.flush()
            emitted = True

    if not emitted:
        logger.warning("=" * 60)
        logger.warning("  ADMIN ACCOUNT CREATED")
        logger.warning(f"  Username: {username}")
        logger.warning("  Initial password is only available on first startup.")
        logger.warning("  Lost it? See docs/operations/admin-recovery.md")
        logger.warning("=" * 60)


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
            logger.warning(f"[init_db] DB not ready (attempt {attempt+1}/30): {e}")
            await asyncio.sleep(1)
    else:
        logger.error("[init_db] DB unreachable after 30s — aborting")
        return

    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(User).where(User.username == "admin"))
            existing = result.scalar_one_or_none()
            if not existing:
                initial_password = secrets.token_urlsafe(16)
                admin = User(
                    username             = "admin",
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
                    _emit_bootstrap_admin_credentials("admin", initial_password)
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
        if debug_mode == "true":
            logging.getLogger("mediakeeper").setLevel(logging.DEBUG)
            if _file_handler is not None:
                _file_handler.setLevel(logging.DEBUG)
            logger.info("Debug mode enabled from configuration")
        else:
            logging.getLogger("mediakeeper").setLevel(logging.INFO)
            if _file_handler is not None:
                _file_handler.setLevel(logging.INFO)

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
        logger.warning(f"Watchlist cache unavailable at startup: {e}")


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
        logger.error("[STARTUP] Achievement seed FAILED", exc_info=True)

    try:
        from core.database import AsyncSessionLocal
        from services.portal.help import ensure_seed as ensure_help_seed
        logger.info("[STARTUP] Seeding help articles...")
        async with AsyncSessionLocal() as seed_db:
            created = await ensure_help_seed(seed_db)
        logger.info("[STARTUP] Help seed done (created=%s)", created)
    except Exception:
        logger.error("[STARTUP] Help seed FAILED", exc_info=True)

    # Prime the image-cache enable flag so ``_normalize`` doesn't
    # silently default to OFF for the first 30 s while the cached
    # snapshot is still empty.
    try:
        from core.database import AsyncSessionLocal
        from services.portal.image_cache import refresh_enabled_flag
        async with AsyncSessionLocal() as seed_db:
            await refresh_enabled_flag(seed_db, force=True)
    except Exception:
        logger.error("[STARTUP] Image cache flag prime FAILED", exc_info=True)

    # Apply the DNS cache toggle right at startup so every outbound
    # call (TMDB, OpenSubtitles, Emby, …) inherits the resolver wrap
    # from the first request onwards.
    try:
        from core.database import AsyncSessionLocal
        from services.portal.dns_cache import refresh_from_settings as dns_refresh
        async with AsyncSessionLocal() as seed_db:
            await dns_refresh(seed_db)
    except Exception:
        logger.error("[STARTUP] DNS cache toggle apply FAILED", exc_info=True)

    if _PROCESS_ROLE in {"combined", "worker"}:
        background_manager = BackgroundTaskManager(engine)
        await background_manager.start()

    yield

    if background_manager is not None:
        await background_manager.stop()
    await close_clients()
    await engine.dispose()
