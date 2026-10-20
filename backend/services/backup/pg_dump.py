"""Run pg_dump for a backup: the database part of the archive."""
from __future__ import annotations

import asyncio
import logging
import os
from urllib.parse import unquote, urlparse

from core.database import DATABASE_URL

logger = logging.getLogger("mediakeeper.backup")


def parse_pg_dsn(database_url: str) -> dict[str, str]:
    """Split a SQLAlchemy/asyncpg DSN into pg_dump connection parts.

    urlparse does not percent-decode credentials; the DSN percent-encodes
    reserved chars (@ : / %). Decode them so pg_dump connects with the same
    values asyncpg uses — else auth fails and the archive silently omits the dump.
    """
    parsed = urlparse(database_url.replace("+asyncpg", ""))
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or "mediakeeper"),
        "password": unquote(parsed.password or ""),
        "dbname": unquote((parsed.path or "/mediakeeper_db").lstrip("/")),
    }


async def dump_database() -> bytes | None:
    """Start pg_dump in a subprocess and return the SQL, kept as bytes: a large
    dump is not copied again by decoding it."""
    dsn = parse_pg_dsn(DATABASE_URL)

    env = os.environ.copy()
    env["PGPASSWORD"] = dsn["password"]

    cmd = [
        "pg_dump",
        "-h", dsn["host"],
        "-p", dsn["port"],
        "-U", dsn["user"],
        "-d", dsn["dbname"],
        "--no-owner", "--no-acl", "--if-exists", "--clean",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except TimeoutError:
        proc.kill()  # else pg_dump keeps running after the backup gave up on it
        await proc.wait()
        raise

    if proc.returncode != 0:
        logger.error("[backup] pg_dump failed: %s", stderr.decode(errors="replace")[:300])
        try:
            from services.monitoring import AlertType, send_alert

            await send_alert(
                AlertType.BACKUP_FAILED,
                {"component": "pg_dump", "returncode": proc.returncode},
            )
        except Exception:
            logger.exception("[backup] Failed to push monitoring alert")
        return None
    return stdout
