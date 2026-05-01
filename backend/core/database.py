import os
from pathlib import Path
from urllib.parse import urlparse, quote
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# ============================================
# Connection URL construction
# ============================================
# Priority:
#   1. DATABASE_URL defined (3 containers OR single entrypoint)
#   2. Single-container fallback: read /data/.pg_password
# ============================================

_raw = os.getenv("DATABASE_URL", "")

if not _raw:
    _pg_pwd_file = Path("/data/.pg_password")
    if _pg_pwd_file.exists():
        _pg_pwd = _pg_pwd_file.read_text().strip()
        _raw = f"postgresql://mediakeeper:{_pg_pwd}@127.0.0.1:5432/mediakeeper_db"
    else:
        raise RuntimeError(
            "DATABASE_URL is not set and /data/.pg_password was not found. "
            "Check your Docker configuration."
        )

_engine_kwargs = {"echo": False}
_db_ssl_enabled = os.getenv("DATABASE_SSL", "false").lower() in ("true", "1", "yes", "on")

if _raw.startswith("sqlite+aiosqlite://"):
    DATABASE_URL = _raw
elif _raw.startswith("sqlite://"):
    DATABASE_URL = _raw.replace("sqlite://", "sqlite+aiosqlite://", 1)
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _parsed = urlparse(_raw)
    _user = _parsed.username or ""
    _pwd  = _parsed.password or ""
    _host = _parsed.hostname or "127.0.0.1"
    _port = _parsed.port or 5432
    _db   = (_parsed.path or "/mediakeeper_db").lstrip("/")
    DATABASE_URL = f"postgresql+asyncpg://{quote(_user, safe='')}:{quote(_pwd, safe='')}@{_host}:{_port}/{_db}"
    _engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "connect_args": {"ssl": _db_ssl_enabled},
    })

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency: provides a DB session."""
    async with AsyncSessionLocal() as session:
        yield session
