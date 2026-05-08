"""Admin / Back-Office security hardening regressions.

Covers:
- ``core.csv_safe.safe_csv_cell`` / ``safe_csv_row`` neutralise spreadsheet
  formula leaders.
- List CSV export passes a dangerous title through the safe writer for
  every dangerous leader (``=``, ``+``, ``-``, ``@``, tab, CR, LF).
- Admin user RGPD CSV export passes a dangerous display_name through.
- Portal ``batch-status``:
    - dedupe runs first and preserves submission order;
    - the unique-id cap rejects bodies whose deduplicated count exceeds
      100;
    - the outer raw-payload guard rejects absurd payloads at validation;
    - ``anonymize_requests=True`` strips ``requested_by``,
      ``requested_by_deleted`` and ``reject_reason`` for non-admin
      callers; admins and ``anonymize_requests=False`` keep
      ``reject_reason``.
"""
from __future__ import annotations

import pytest

from api.portal.requests import (
    BATCH_STATUS_MAX_IDS,
    BATCH_STATUS_MAX_RAW_IDS,
    _dedupe_keep_order,
)
from core.csv_safe import safe_csv_cell, safe_csv_row
from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.portal.social import UserList, UserListItem
from models.user import User
from services.settings import set_setting


# ─── helpers ───


def _portal_auth(client, user: User) -> None:
    client.cookies.set(
        "rq_token",
        create_access_token({"sub": user.username, "scope": "portal"}),
    )


def _admin_auth(client, user: User) -> None:
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": user.username, "scope": "admin"}),
    )


async def _make_user(db, username: str, *, role: str = "viewer") -> User:
    user = User(
        username=username,
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(UserProfile(
        user_id=user.id, display_name=username,
        role=role, account_active=True,
    ))
    await db.commit()
    return user


# ─── unit: core.csv_safe ───


@pytest.mark.parametrize("value", [
    "Mon top 100",
    "Studio Ghibli",
    "1999",
    "",
    None,
    42,
    True,
])
def test_safe_csv_cell_keeps_safe_values_intact(value):
    assert safe_csv_cell(value) == value


@pytest.mark.parametrize("dangerous", [
    "=cmd|'/c calc'!A0",
    "+1+1",
    "-2+2",
    "@SUM(A1:A10)",
    "\tinjection",
    "\rinjection",
    "\ninjection",
    "   =leadingspaces",
])
def test_safe_csv_cell_prefixes_dangerous_leaders(dangerous):
    out = safe_csv_cell(dangerous)
    assert isinstance(out, str)
    assert out.startswith("'")
    assert out[1:] == dangerous


def test_safe_csv_row_neutralises_each_cell():
    row = ["Title", "=BAD()", 2024, "+also bad"]
    out = safe_csv_row(row)
    assert out[0] == "Title"
    assert out[1] == "'=BAD()"
    assert out[2] == 2024
    assert out[3] == "'+also bad"


# ─── list CSV export ───


@pytest.mark.asyncio
@pytest.mark.parametrize("dangerous_title", [
    "=cmd|'/c calc'!A0",
    "+1+1",
    "-2+2",
    "@SUM(A1:A10)",
    "\tinjection",
    "\rinjection",
    "\ninjection",
])
async def test_list_csv_export_neutralises_dangerous_title(
    client, db_session, dangerous_title,
):
    """Every dangerous leader must be apostrophe-prefixed in the
    exported CSV — opening the file in a spreadsheet renders the
    literal text instead of evaluating a formula."""
    # Each parametrize value gets a fresh user/list; usernames stay
    # unique by leveraging the title hash.
    user = await _make_user(db_session, f"exp-{abs(hash(dangerous_title))}")
    lst = UserList(
        user_id=user.id,
        name="My list",
        privacy="private",
        content_type="movies",
    )
    db_session.add(lst)
    await db_session.commit()
    await db_session.refresh(lst)

    db_session.add(UserListItem(
        list_id=lst.id,
        tmdb_id=1,
        media_type="movie",
        title=dangerous_title,
        year=2024,
    ))
    await db_session.commit()

    _portal_auth(client, user)
    resp = await client.get(f"/api/portal/lists/{lst.id}/export?fmt=csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    body = resp.text

    # No data line may begin with one of the dangerous leaders or with
    # a quoted dangerous leader. The header row is OK because its
    # cells are static ASCII labels.
    data_lines = [line for line in body.splitlines() if line]
    # Skip the header (first non-empty line, BOM-prefixed).
    for line in data_lines[1:]:
        first = line[0]
        assert first not in ("=", "+", "-", "@", "\t"), (
            f"Data line started with dangerous leader {first!r}: {line!r}"
        )
        if first == '"':
            # csv writer quotes any cell that contains a quote, comma,
            # CR, or LF. The first character inside the quoted cell
            # must not be a dangerous leader.
            assert line[1] not in ("=", "+", "-", "@", "\t"), (
                f"Quoted cell still leads with {line[1]!r}: {line!r}"
            )


# ─── admin user RGPD CSV export ───


@pytest.mark.asyncio
@pytest.mark.parametrize("dangerous_payload", [
    "=HYPERLINK(\"http://evil\",\"click\")",
    "+SUM(1,2)",
    "-2+3",
    "@cmd",
    "\ttabbed",
])
async def test_admin_user_csv_export_neutralises_dangerous_display_name(
    client, admin_user, db_session, dangerous_payload,
):
    """A dangerous display_name flowing through the RGPD CSV export
    must be apostrophe-prefixed in the value column so the spreadsheet
    renders it as a literal."""
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()
    _admin_auth(client, admin_user)

    target = User(
        username=f"target-{abs(hash(dangerous_payload))}",
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(target)
    await db_session.commit()
    await db_session.refresh(target)

    profile = UserProfile(
        user_id=target.id,
        display_name=dangerous_payload,
        role="viewer",
        source="local",
        account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    resp = await client.get(
        f"/api/portal/admin/users/{profile.id}/export?format=csv",
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    body = resp.text

    # No data line may begin with one of the dangerous leaders, neither
    # raw nor inside a quoted cell.
    for line in body.splitlines()[1:]:
        if not line:
            continue
        assert line[0] not in ("=", "+", "-", "@", "\t"), (
            f"Data line started with {line[0]!r}: {line!r}"
        )
        if line[0] == '"':
            assert line[1] not in ("=", "+", "-", "@", "\t"), (
                f"Quoted cell led with {line[1]!r}: {line!r}"
            )


# ─── batch-status: dedupe helper unit ───


def test_dedupe_keep_order_drops_duplicates_only():
    assert _dedupe_keep_order([3, 1, 2, 1, 3, 2, 4]) == [3, 1, 2, 4]


def test_dedupe_keep_order_handles_empty_and_singleton():
    assert _dedupe_keep_order([]) == []
    assert _dedupe_keep_order([42]) == [42]


def test_dedupe_keep_order_preserves_first_occurrence():
    """First sighting wins so the original priority of a feed page is kept."""
    seq = [10, 20, 10, 30, 20, 10, 40]
    assert _dedupe_keep_order(seq) == [10, 20, 30, 40]


# ─── batch-status: HTTP cap + dedupe ───


@pytest.mark.asyncio
async def test_batch_status_rejects_above_unique_cap(client, db_session):
    """101 unique ids → 422 (unique cap)."""
    user = await _make_user(db_session, "capper")
    _portal_auth(client, user)
    payload = {"tmdb_ids": list(range(1, BATCH_STATUS_MAX_IDS + 2))}
    resp = await client.post("/api/portal/requests/batch-status", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_status_accepts_exactly_cap(client, db_session):
    """Exactly 100 unique ids → 200."""
    user = await _make_user(db_session, "capper2")
    _portal_auth(client, user)
    payload = {"tmdb_ids": list(range(1, BATCH_STATUS_MAX_IDS + 1))}
    resp = await client.post("/api/portal/requests/batch-status", json=payload)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_batch_status_dedupes_then_caps_unique_count(client, db_session):
    """200 raw ids but only 50 unique → accepted: dedupe runs first,
    the cap applies on the unique count, not the raw payload size."""
    user = await _make_user(db_session, "dedupcap")
    _portal_auth(client, user)
    unique = list(range(1, 51))  # 50 unique
    raw = unique + unique + unique + unique  # 200 raw, still 50 unique
    assert len(raw) == 200
    resp = await client.post(
        "/api/portal/requests/batch-status", json={"tmdb_ids": raw},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_batch_status_rejects_outer_raw_cap(client, db_session):
    """Beyond the outer raw guard (10× the unique cap), Pydantic rejects
    the payload at validation — that path also returns 422."""
    user = await _make_user(db_session, "outercap")
    _portal_auth(client, user)
    payload = {"tmdb_ids": list(range(1, BATCH_STATUS_MAX_RAW_IDS + 2))}
    resp = await client.post("/api/portal/requests/batch-status", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_status_dedupes_input(client, db_session):
    user = await _make_user(db_session, "deduper")
    db_session.add(MediaRequest(
        user_id=user.id,
        tmdb_id=42,
        media_type="movie",
        title="Demo",
        status="pending",
    ))
    await db_session.commit()

    _portal_auth(client, user)
    # Same id repeated 5 times — must collapse to one entry.
    resp = await client.post(
        "/api/portal/requests/batch-status",
        json={"tmdb_ids": [42, 42, 42, 42, 42]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert list(body["results"].keys()) == ["42"]
    assert body["results"]["42"]["status"] == "pending"


@pytest.mark.asyncio
async def test_batch_status_dedupe_passes_ordered_ids_to_service(
    client, db_session, monkeypatch,
):
    """The route must dedupe while preserving submission order before
    handing the list to the service. Spy on ``get_batch_status`` to
    confirm the exact list it received."""
    user = await _make_user(db_session, "orderspy")
    captured: dict = {}

    async def _spy(db, ids, *, anonymize: bool = False):  # noqa: ARG001
        captured["ids"] = list(ids)
        return {}

    monkeypatch.setattr(
        "services.portal.requests.get_batch_status", _spy,
    )

    _portal_auth(client, user)
    submitted = [9, 5, 5, 7, 9, 3, 7, 1]
    resp = await client.post(
        "/api/portal/requests/batch-status",
        json={"tmdb_ids": submitted},
    )
    assert resp.status_code == 200
    assert captured["ids"] == [9, 5, 7, 3, 1]


# ─── anonymize_requests: reject_reason masking ───


async def _seed_rejected_request(db, user_id: int, tmdb_id: int) -> int:
    req = MediaRequest(
        user_id=user_id,
        tmdb_id=tmdb_id,
        media_type="movie",
        title="Refused",
        status="rejected",
        reject_reason="duplicate_of_42",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req.id


@pytest.mark.asyncio
async def test_batch_status_anonymize_strips_reject_reason_for_non_admin(
    client, db_session,
):
    requester = await _make_user(db_session, "requester1")
    viewer = await _make_user(db_session, "viewer1")
    await _seed_rejected_request(db_session, requester.id, tmdb_id=900)
    await set_setting(db_session, "portal.anonymize_requests", "true")

    _portal_auth(client, viewer)
    resp = await client.post(
        "/api/portal/requests/batch-status", json={"tmdb_ids": [900]},
    )
    assert resp.status_code == 200
    entry = resp.json()["results"]["900"]
    assert entry["status"] == "rejected"
    assert "reject_reason" not in entry
    assert "requested_by" not in entry
    assert "requested_by_deleted" not in entry


@pytest.mark.asyncio
async def test_batch_status_anonymize_keeps_reject_reason_for_admin(
    client, db_session,
):
    requester = await _make_user(db_session, "requester2")
    admin = await _make_user(db_session, "admin2", role="admin")
    await _seed_rejected_request(db_session, requester.id, tmdb_id=901)
    await set_setting(db_session, "portal.anonymize_requests", "true")

    _portal_auth(client, admin)
    resp = await client.post(
        "/api/portal/requests/batch-status", json={"tmdb_ids": [901]},
    )
    assert resp.status_code == 200
    entry = resp.json()["results"]["901"]
    assert entry["status"] == "rejected"
    assert entry["reject_reason"] == "duplicate_of_42"
    assert entry["requested_by"] == "requester2"


@pytest.mark.asyncio
async def test_batch_status_no_anonymize_keeps_reject_reason(
    client, db_session,
):
    requester = await _make_user(db_session, "requester3")
    viewer = await _make_user(db_session, "viewer3")
    await _seed_rejected_request(db_session, requester.id, tmdb_id=902)
    # Flag stays at its default (False) — no setting override.

    _portal_auth(client, viewer)
    resp = await client.post(
        "/api/portal/requests/batch-status", json={"tmdb_ids": [902]},
    )
    assert resp.status_code == 200
    entry = resp.json()["results"]["902"]
    assert entry["reject_reason"] == "duplicate_of_42"
    assert entry["requested_by"] == "requester3"
