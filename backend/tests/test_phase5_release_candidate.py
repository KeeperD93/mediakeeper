import pytest

from core.security import create_access_token
from services.logs import MAX_LOG_LINES


@pytest.mark.asyncio
async def test_logs_read_rejects_more_than_max_lines(client, admin_user):
    client.cookies.set("mk_token", create_access_token({"sub": admin_user.username}))

    resp = await client.get(f"/api/logs/read/mediakeeper.txt?lines={MAX_LOG_LINES + 1}")

    assert resp.status_code == 422
