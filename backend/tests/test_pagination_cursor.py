"""Cursor pagination decode robustness (forged / malformed input)."""
from __future__ import annotations

import base64
import json

from core.pagination import decode_cursor, encode_cursor


def _raw_cursor(payload) -> str:
    """Encode an arbitrary JSON payload as a cursor (bypasses encode_cursor's dict contract)."""
    raw = json.dumps(payload)
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def test_round_trip_preserves_int_id():
    assert decode_cursor(encode_cursor({"id": 42})) == {"id": 42}


def test_empty_cursor_returns_none():
    assert decode_cursor("") is None


def test_malformed_base64_returns_none():
    assert decode_cursor("!!!not-valid-base64!!!") is None


def test_non_dict_payload_returns_none():
    # A bare list or scalar must never reach a consumer expecting a dict.
    assert decode_cursor(_raw_cursor([1, 2])) is None
    assert decode_cursor(_raw_cursor(5)) is None


def test_forged_non_integer_id_returns_none():
    # The core regression: {"id": "abc"} would crash `WHERE id < 'abc'` on PostgreSQL.
    assert decode_cursor(_raw_cursor({"id": "abc"})) is None


def test_numeric_string_id_is_coerced_to_int():
    assert decode_cursor(_raw_cursor({"id": "7"})) == {"id": 7}


def test_dict_without_int_field_passes_through():
    # No "id" key → nothing to coerce; consumers guard on `"id" in decoded`.
    assert decode_cursor(_raw_cursor({"foo": "bar"})) == {"foo": "bar"}


def test_compound_cursor_round_trip():
    cursor = encode_cursor({"severity_rank": 2, "id": 7})
    assert decode_cursor(cursor, int_fields=("id", "severity_rank")) == {
        "severity_rank": 2,
        "id": 7,
    }


def test_forged_compound_severity_rank_returns_none():
    cursor = _raw_cursor({"id": 5, "severity_rank": "x"})
    assert decode_cursor(cursor, int_fields=("id", "severity_rank")) is None


def test_forged_boolean_id_returns_none():
    # int(True) == 1 would otherwise smuggle a boolean through as a valid id.
    assert decode_cursor(_raw_cursor({"id": True})) is None
    assert decode_cursor(_raw_cursor({"id": False})) is None
