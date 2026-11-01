"""A refused sign-in says how long the block lasts, when it has an end."""
import ast
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

from constants.security import TEMP_BLOCK_SECONDS
from services.security import create_block, ensure_not_blocked

HOME = "198.51.100.7"
BACKEND_ROOT = Path(__file__).resolve().parent.parent


async def _block_until(db_session, *, seconds: int, ip: str | None = None, username: str | None = None) -> None:
    until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    await create_block(
        db_session, admin_id=None, ip=ip, username=username, scope="portal", permanent=False, blocked_until=until,
    )


async def _refusal_headers(db_session, scope: str = "portal") -> dict:
    with pytest.raises(HTTPException) as refused:
        await ensure_not_blocked(db_session, HOME, "member-a", scope)
    assert refused.value.status_code == 429
    assert refused.value.detail == "login_blocked"
    return refused.value.headers or {}


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/portal-login"])
@pytest.mark.asyncio
async def test_a_failed_tries_block_answers_with_its_wait(client, path):
    """Stored without a time zone by the test database, read back as UTC."""
    for _ in range(3):
        resp = await client.post(path, json={"username": "member-a", "password": "Wrong-Synthetic-1!"})
        assert resp.status_code == 401

    resp = await client.post(path, json={"username": "member-a", "password": "Wrong-Synthetic-1!"})

    assert (resp.status_code, resp.json()["detail"]) == (429, "login_blocked")
    assert 1 <= int(resp.headers["Retry-After"]) <= TEMP_BLOCK_SECONDS


@pytest.mark.asyncio
async def test_a_block_that_never_ends_gives_no_wait(db_session):
    await create_block(db_session, admin_id=None, ip=None, username="member-a", scope="portal", permanent=True)

    assert "Retry-After" not in await _refusal_headers(db_session)


@pytest.mark.asyncio
async def test_the_wait_is_for_the_last_block_to_end(db_session):
    """Each block refuses alone: the first end would only lead to another refusal."""
    await _block_until(db_session, seconds=60, username="member-a")
    await _block_until(db_session, seconds=540, ip=HOME)

    assert 530 <= int((await _refusal_headers(db_session))["Retry-After"]) <= 540


@pytest.mark.asyncio
async def test_a_block_that_never_ends_outweighs_a_timed_one(db_session):
    await _block_until(db_session, seconds=60, username="member-a")
    await create_block(db_session, admin_id=None, ip=HOME, username=None, scope="all", permanent=True)

    assert "Retry-After" not in await _refusal_headers(db_session)


@pytest.mark.asyncio
async def test_an_ended_block_and_another_scope_do_not_lengthen_the_wait(db_session):
    await _block_until(db_session, seconds=60, username="member-a")
    await _block_until(db_session, seconds=-60, ip=HOME)
    await create_block(
        db_session, admin_id=None, ip=HOME, username=None, scope="admin", permanent=False,
        blocked_until=datetime.now(timezone.utc) + timedelta(seconds=540),
    )

    assert 50 <= int((await _refusal_headers(db_session))["Retry-After"]) <= 60


@pytest.mark.asyncio
async def test_the_wait_never_reads_zero(db_session):
    """A block ending right now is still in force: the page must not say "0 s"."""
    await _block_until(db_session, seconds=0.2, username="member-a")

    assert int((await _refusal_headers(db_session))["Retry-After"]) >= 1


@pytest.mark.parametrize("env", [
    {"FRONTEND_ORIGIN": "https://app.example", "MK_DEBUG": ""},
    {"MK_DEBUG": "true", "ENV": "", "ENVIRONMENT": ""},
])
def test_a_page_served_from_another_origin_can_read_the_wait(env):
    """Both CORS setups are chosen at import, hence the fresh process. Without this,
    the browser hides the header from the page, which then shows no wait."""
    code = (
        "import main; print([m.kwargs['expose_headers'] for m in main.app.user_middleware "
        "if m.cls.__name__ == 'CORSMiddleware'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT, env={**os.environ, **env}, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert ast.literal_eval(result.stdout.strip().splitlines()[-1]) == [["Retry-After"]]
