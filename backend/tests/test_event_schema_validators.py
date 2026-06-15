"""Schema-level validation for the seasonal-event / watch-party create payloads.

``CreateEvent`` / ``CreateParty`` guard the API boundary before the service
layer: they require timezone-aware datetimes and reject an inverted seasonal
window. These unit tests pin those validators directly — the service functions
take raw dicts and would bypass them.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from api.portal._events_rooms import (
    MKEventMedia, RespondPayload, RoomMessage, UpdateMKEvent,
)
from api.portal._events_seasonal import CreateEvent, CreateParty


def _aware(offset_days: float = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=offset_days)


def test_create_event_accepts_aware_forward_window():
    ev = CreateEvent(name="Spring", start_date=_aware(0), end_date=_aware(30))
    assert ev.start_date.tzinfo is not None
    assert ev.end_date > ev.start_date


def test_create_event_rejects_inverted_window():
    with pytest.raises(ValidationError):
        CreateEvent(name="Spring", start_date=_aware(30), end_date=_aware(0))


def test_create_event_rejects_zero_length_window():
    same = _aware(5)
    with pytest.raises(ValidationError):
        CreateEvent(name="Spring", start_date=same, end_date=same)


def test_create_event_rejects_naive_dates():
    naive = datetime.now()  # noqa: DTZ005 — intentionally naive to assert rejection
    with pytest.raises(ValidationError):
        CreateEvent(name="Spring", start_date=naive, end_date=naive + timedelta(days=1))


def test_create_party_accepts_aware():
    party = CreateParty(title="Movie night", scheduled_at=_aware(1))
    assert party.scheduled_at.tzinfo is not None


def test_create_party_rejects_naive():
    with pytest.raises(ValidationError):
        CreateParty(title="Movie night", scheduled_at=datetime.now())  # noqa: DTZ005


def test_seasonal_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        CreateEvent(name="Spring", start_date=_aware(0), end_date=_aware(30), bogus=1)
    with pytest.raises(ValidationError):
        CreateParty(title="Movie night", scheduled_at=_aware(1), bogus=1)


def test_room_schemas_reject_unknown_fields():
    with pytest.raises(ValidationError):
        MKEventMedia(tmdb_id=1, media_type="movie", title="X", bogus=1)
    with pytest.raises(ValidationError):
        UpdateMKEvent(title="X", bogus=1)
    with pytest.raises(ValidationError):
        RespondPayload(decision="accept", bogus=1)
    with pytest.raises(ValidationError):
        RoomMessage(content="hi", bogus=1)
