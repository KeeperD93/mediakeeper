"""Schema-level guard: the category and subtitle mutation endpoints reject
unknown body fields (``ConfigDict(extra="forbid")``) so a probing payload on
these destructive mutations (write/delete .srt, remove embedded streams,
create a category) is rejected with 422 instead of being silently ignored.

The free-form ``list[dict]`` payloads (``BatchDownloadRequest.items``,
``BatchRemoveStreamRequest.operations``) keep their unrestricted inner keys —
``extra="forbid"`` only guards the top-level model fields here.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.media._categories import CategoryRequest
from api.subtitles._schemas import (
    BatchDownloadRequest,
    BatchRemoveStreamRequest,
    DeleteRequest,
    DownloadRequest,
    FixEncodingRequest,
    ProfileRequest,
    RemoveStreamRequest,
    RemoveStreamsBatchRequest,
    ShiftSrtRequest,
)


@pytest.mark.parametrize("model, valid", [
    (CategoryRequest, {"label": "Films", "path": "/m"}),
    (DownloadRequest, {"file_id": 1, "destination": "/x.srt"}),
    (DeleteRequest, {"path": "/x.srt"}),
    (RemoveStreamRequest, {"item_id": "i", "stream_index": 1}),
    (RemoveStreamsBatchRequest, {"item_id": "i", "stream_indices": [1, 2]}),
    (BatchRemoveStreamRequest, {"operations": [{"item_id": "i", "stream_index": 1}]}),
    (BatchDownloadRequest, {"items": [{"imdb_id": "tt1"}]}),
    (ShiftSrtRequest, {"path": "/x.srt", "offset_ms": 100}),
    (FixEncodingRequest, {"path": "/x.srt"}),
    (ProfileRequest, {"name": "Default"}),
])
def test_category_subtitle_mutation_schemas_reject_extra_field(model, valid):
    model(**valid)
    with pytest.raises(ValidationError):
        model(**valid, unexpected="x")
