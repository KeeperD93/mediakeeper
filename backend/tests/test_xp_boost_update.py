"""Effective-window validation for partial XP boost event updates.

A single-field date edit must be checked against the stored bound it isn't
replacing — otherwise an admin can invert a campaign window by moving only one
side. These service-level tests pin that merge-then-validate guard.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.portal import xp_boost as svc


async def _create(db, *, start_offset_days: float = 0, end_offset_days: float = 10):
    now = datetime.now(timezone.utc)
    return await svc.create_event(db, {
        "name": "Double XP",
        "starts_at": now + timedelta(days=start_offset_days),
        "ends_at": now + timedelta(days=end_offset_days),
    })


@pytest.mark.asyncio
async def test_update_start_past_existing_end_rejected(db_session):
    ev = await _create(db_session)  # window now → now+10d
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        await svc.update_event(db_session, ev["id"], {"starts_at": now + timedelta(days=20)})


@pytest.mark.asyncio
async def test_update_end_before_existing_start_rejected(db_session):
    ev = await _create(db_session, start_offset_days=5, end_offset_days=15)
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        await svc.update_event(db_session, ev["id"], {"ends_at": now + timedelta(days=1)})


@pytest.mark.asyncio
async def test_update_both_inverted_rejected(db_session):
    ev = await _create(db_session)
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        await svc.update_event(db_session, ev["id"], {
            "starts_at": now + timedelta(days=10),
            "ends_at": now + timedelta(days=2),
        })


@pytest.mark.asyncio
async def test_update_name_only_keeps_window(db_session):
    ev = await _create(db_session)
    result = await svc.update_event(db_session, ev["id"], {"name": "Renamed"})
    assert result["name"] == "Renamed"


@pytest.mark.asyncio
async def test_update_single_date_still_valid_ok(db_session):
    ev = await _create(db_session)  # window now → now+10d
    now = datetime.now(timezone.utc)
    result = await svc.update_event(db_session, ev["id"], {"ends_at": now + timedelta(days=30)})
    assert result is not None
