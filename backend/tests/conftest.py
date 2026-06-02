"""
Fixtures pytest for Mediakeeper.
Uses an async in-memory SQLite DB for tests (no PostgreSQL required).
"""

import os
import sys
import shutil
import tempfile
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path

# Forcer les variables d'env AVANT tout import applicatif
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only-012345"
os.environ["JWT_EXPIRE_MINUTES"] = "60"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401  # Ensure every model is registered in Base.metadata
# Importing ``main`` at conftest load time guarantees that every top-level
# model file (security, healthcheck, scheduler…) is imported before
# ``setup_db`` runs ``Base.metadata.create_all``. Without this, isolated
# test runs (``pytest -k single_test``) hit ``no such table`` errors
# because ``models/__init__.py`` only re-exports the portal submodule.
import main  # noqa: F401, E402
from models.base import Base
from models.user import User
from core.security import hash_password


# Engine SQLite async for tests.
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
)


# SQLite ignores foreign-key constraints unless told otherwise. Enabling
# the pragma on every connection lets ``ON DELETE CASCADE`` /
# ``ON DELETE SET NULL`` behave like Postgres in production and exposes
# missing-FK bugs early.
from sqlalchemy import event as _sa_event  # noqa: E402


@_sa_event.listens_for(_test_engine.sync_engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
    finally:
        cursor.close()

_TestSession = sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
def workspace_tmp_path():
    """Temporary directory inside the workspace to avoid system Temp issues under sandbox."""
    base = BACKEND_ROOT / ".pytest-temp"
    base.mkdir(exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="mk-", dir=base))
    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create the tables before each test and drop them after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear slowapi's in-memory buckets between tests so a noisy
    rate-limit test cannot starve an unrelated one. Cheap (memory-only
    reset) so applying it globally has no measurable cost."""
    from core.rate_limit import limiter
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def _reset_media_categories_cache():
    """Drop the module-level media-categories cache between tests.
    Without this, a test that triggers load_categories/save_categories
    leaks the populated list into unrelated tests that assume a fresh
    DB (and therefore zero configured folders)."""
    from services.media_manager import categories as _cat
    _cat._categories_cache.clear()
    yield
    _cat._categories_cache.clear()


@pytest.fixture(autouse=True)
def _reset_diagnostic_log_sentinels():
    """Restore the WARN-once cooldown sentinels to their module-init
    value (-inf) between tests. The CSRF middleware and the WS
    upgrade fallback mutate them on the first hostile request, and
    the regression guard test_diagnostic_log_sentinels_pass_cooldown_at_boot
    asserts the module-init state — without this reset it depends on
    the order in which any other test fires those code paths."""
    import api.portal.chat as _chat
    import core.csrf_middleware as _mw
    _mw._last_origin_mismatch_log = float("-inf")
    _chat._last_ws_upgrade_log = float("-inf")
    yield
    _mw._last_origin_mismatch_log = float("-inf")
    _chat._last_ws_upgrade_log = float("-inf")


@pytest_asyncio.fixture
async def db_session():
    """Fournit une session DB de test."""
    async with _TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create a test admin user."""
    user = User(
        username="admin",
        hashed_password=hash_password("TestPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def portal_login():
    """Return an async helper that logs a user into the portal via the
    cascade login. Callers pass their own HTTP client (seeded ``client`` or
    bare ``raw_client``); credentials default to the ``admin_user`` fixture."""
    async def _login(http_client, *, username: str = "admin", password: str = "TestPassword123!"):
        r = await http_client.post("/api/auth/portal-login", json={
            "username": username,
            "password": password,
        })
        assert r.status_code == 200, r.text
        return r
    return _login


async def _build_client(seed_csrf: bool):
    """Shared factory for the test HTTP client — see the two fixtures below."""
    from core.database import get_db
    from core import app_startup
    import main as main_module
    app = main_module.app

    async def _override_get_db():
        async with _TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    previous_db_ready = app_startup._db_ready
    app_startup._db_ready = True

    with patch("core.http_client.init_clients", new_callable=AsyncMock), \
         patch("core.http_client.close_clients", new_callable=AsyncMock), \
         patch("services.stats.collect_active_sessions", new_callable=AsyncMock), \
         patch("services.stats.refresh_library_cache", new_callable=AsyncMock), \
         patch("services.watchlist.run_background_scan", new_callable=AsyncMock), \
         patch("services.notification_engine.check_and_send_notifications", new_callable=AsyncMock), \
         patch("services.logs.fetch_and_store_emby_logs", new_callable=AsyncMock):

        transport = ASGITransport(app=app)
        kwargs: dict = {"transport": transport, "base_url": "http://test"}
        if seed_csrf:
            # 42 chars in the [A-Za-z0-9_-] charset so the value passes the
            # production allowlist guard (api/auth/_csrf._CSRF_TOKEN_RE) and
            # is preserved by ensure_csrf_cookie on polls.
            csrf_token = "pytest-csrf-token-padded-to-pass-allowlist"
            kwargs["headers"] = {"X-CSRF-Token": csrf_token}
            kwargs["cookies"] = {"mk_csrf": csrf_token}

        async with AsyncClient(**kwargs) as ac:
            if seed_csrf:
                # Keep the X-CSRF-Token header in lockstep with whatever
                # mk_csrf value the server returns. Auth boundaries
                # (login, change-password) rotate the cookie on success;
                # without this hook the seeded header would go stale and
                # every subsequent mutation would 403 csrf_token_invalid.
                # A real SPA does the equivalent by reading document.cookie
                # before each mutation.
                async def _sync_csrf_header(response):
                    new_csrf = response.cookies.get("mk_csrf")
                    if new_csrf:
                        ac.headers["X-CSRF-Token"] = new_csrf

                ac.event_hooks.setdefault("response", []).append(_sync_csrf_header)
            yield ac

    app.dependency_overrides.clear()
    app_startup._db_ready = previous_db_ready


@pytest_asyncio.fixture
async def client(db_session):
    """Default test client — auto-seeds a CSRF cookie + header so mutation
    tests don't have to replay the full browser handshake on every call."""
    async for c in _build_client(seed_csrf=True):
        yield c


@pytest_asyncio.fixture
async def raw_client(db_session):
    """Test client without any CSRF seeding. Use this for tests that
    exercise the CSRF middleware itself (origin mismatch, missing header…)."""
    async for c in _build_client(seed_csrf=False):
        yield c
