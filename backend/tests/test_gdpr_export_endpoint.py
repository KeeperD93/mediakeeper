"""HTTP-level tests for ``GET /api/portal/me/export``.

Covers:

* gating (404 when ``gdpr.enabled`` is ``false``),
* ZIP shape (Content-Type, attachment filename, README + JSON files),
* rate limit (1/h),
* 50 MB guard (synthetic blow-up via monkeypatch).
"""
import io
import zipfile

import pytest

from services.settings import set_setting
from tests._portal_profile_helpers import (
    PORTAL_COOKIE,
    make_portal_user,
    portal_token,
)


async def _enable_gdpr(db_session) -> None:
    await set_setting(db_session, "gdpr.enabled", "true")


async def _seed_user(client, db_session, *, username="exporter"):
    user, profile = await make_portal_user(
        db_session, username=username, role="viewer"
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(username))
    return user, profile


# ---------------------------------------------------------------------------
# Gating
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_returns_404_when_gdpr_disabled(client, db_session):
    await _seed_user(client, db_session, username="gated-off")

    resp = await client.get("/api/portal/me/export")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Not found"}


@pytest.mark.asyncio
async def test_export_requires_authentication(client, db_session):
    await _enable_gdpr(db_session)

    resp = await client.get("/api/portal/me/export")
    # No cookie set on the client → portal deps reject before the
    # gating check would have a chance to run.
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_returns_zip_with_readme_and_json_tables(client, db_session):
    await _enable_gdpr(db_session)
    await _seed_user(client, db_session, username="zip-shape")

    resp = await client.get("/api/portal/me/export")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"

    disposition = resp.headers["content-disposition"]
    assert "attachment" in disposition
    assert "mediakeeper-export-zip-shape-" in disposition
    assert disposition.endswith('.zip"')

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        assert "metadata.json" in names
        # Every table the kickoff promised must have its own JSON file.
        for tbl in (
            "user_profile",
            "user_preferences",
            "user_lists",
            "user_list_items",
            "user_ratings",
            "user_achievements",
            "release_reminders",
            "chat_messages",
            "media_requests",
            "request_votes",
            "watch_party_participants",
            "user_login_history",
        ):
            assert f"{tbl}.json" in names


@pytest.mark.asyncio
async def test_export_filename_carries_username_and_yyyymmdd(client, db_session):
    await _enable_gdpr(db_session)
    await _seed_user(client, db_session, username="datestamp")

    resp = await client.get("/api/portal/me/export")
    assert resp.status_code == 200
    disposition = resp.headers["content-disposition"]
    # ``attachment; filename="mediakeeper-export-datestamp-YYYYMMDD.zip"``
    assert "mediakeeper-export-datestamp-" in disposition
    # 8-digit calendar stamp before ".zip".
    import re
    match = re.search(r"datestamp-(\d{8})\.zip", disposition)
    assert match is not None
    assert len(match.group(1)) == 8


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_is_rate_limited_to_one_per_hour(client, db_session):
    await _enable_gdpr(db_session)
    await _seed_user(client, db_session, username="rl-export")

    first = await client.get("/api/portal/me/export")
    assert first.status_code == 200

    second = await client.get("/api/portal/me/export")
    assert second.status_code == 429


# ---------------------------------------------------------------------------
# 50 MB guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_returns_413_when_zip_payload_exceeds_50mb(
    client, db_session, monkeypatch,
):
    """The endpoint refuses to ship an archive larger than the
    configured cap so a runaway dataset can never DoS the worker."""
    await _enable_gdpr(db_session)
    await _seed_user(client, db_session, username="too-big")

    # Drop the cap to a tiny value so the test stays fast and the
    # synthetic blow-up doesn't have to actually materialise 50 MB.
    monkeypatch.setattr(
        "services.portal._gdpr_export.EXPORT_MAX_BYTES", 16,
    )

    resp = await client.get("/api/portal/me/export")
    assert resp.status_code == 413
    assert resp.json() == {"detail": "export_too_large"}
