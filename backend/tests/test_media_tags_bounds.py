"""Bounds on the media category-tags payload.

The ``/api/media/tags`` setting stores every per-file badge in one JSON row.
``TagsRequest`` caps the entry count and the key/value sizes so the row can't
be grown without limit (admin-only DoS). These unit tests pin those caps.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.media._tags import MAX_KEY_LENGTH, MAX_TAGS, MAX_VALUE_LENGTH, TagsRequest


def test_accepts_a_normal_payload():
    req = TagsRequest(tags={"movie.mkv": {"label": "Action", "color": "#f00", "cat": "movies"}})
    assert "movie.mkv" in req.tags


def test_rejects_too_many_entries():
    with pytest.raises(ValidationError):
        TagsRequest(tags={str(i): {} for i in range(MAX_TAGS + 1)})


def test_rejects_oversized_key():
    with pytest.raises(ValidationError):
        TagsRequest(tags={"x" * (MAX_KEY_LENGTH + 1): {}})


def test_rejects_oversized_value():
    with pytest.raises(ValidationError):
        TagsRequest(tags={"f.mkv": {"blob": "x" * (MAX_VALUE_LENGTH + 1)}})
