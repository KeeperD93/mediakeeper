"""Schema-level guard: the watchlist mutation endpoints reject unknown body
fields (``ConfigDict(extra="forbid")``) so a probing payload on track/untrack/
ignore is rejected with 422 instead of being silently ignored.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.watchlist import IgnoreRequest, TrackRequest, UntrackRequest


@pytest.mark.parametrize("model, valid", [
    (IgnoreRequest, {"keys": ["123_s1_e1"]}),
    (TrackRequest, {"tmdb_id": 42, "media_type": "tv"}),
    (UntrackRequest, {"tmdb_id": 42, "media_type": "tv"}),
])
def test_watchlist_mutation_schemas_reject_extra_field(model, valid):
    model(**valid)
    with pytest.raises(ValidationError):
        model(**valid, unexpected="x")
