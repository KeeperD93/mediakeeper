"""Schema-level guard: the move/delete/folder endpoints reject unknown
body fields (``ConfigDict(extra="forbid")``) so a probing payload on these
destructive media-manager mutations is rejected with 422 instead of being
silently ignored.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.media._move import (
    BatchDeleteRequest,
    CheckConflictsRequest,
    CreateFoldersRequest,
    DeleteRequest,
    FolderItem,
    MoveCatRequest,
    MoveOverwriteRequest,
    MoveRequest,
)


def test_move_schemas_accept_typical_payload():
    assert DeleteRequest(path="/x.mkv").path == "/x.mkv"
    assert MoveRequest(src_path="/a", dest_folder="/b").dest_folder == "/b"
    folders = CreateFoldersRequest(
        folders=[FolderItem(parent_path="/m", folder_name="S01")]
    ).folders
    assert folders[0].folder_name == "S01"


@pytest.mark.parametrize("model, valid", [
    (DeleteRequest, {"path": "/x.mkv"}),
    (MoveCatRequest, {"src_path": "/a", "src_cat": "Films", "dest_cat": "Series"}),
    (BatchDeleteRequest, {"paths": ["/a"]}),
    (FolderItem, {"parent_path": "/m", "folder_name": "x"}),
    (CreateFoldersRequest, {"folders": []}),
    (MoveRequest, {"src_path": "/a", "dest_folder": "/b"}),
    (CheckConflictsRequest, {"file_names": ["a.mkv"], "dest_folder": "/b"}),
    (MoveOverwriteRequest, {"src_path": "/a", "dest_folder": "/b"}),
])
def test_move_schemas_reject_extra_field(model, valid):
    model(**valid)
    with pytest.raises(ValidationError):
        model(**valid, unexpected="x")


def test_create_folders_rejects_extra_key_in_nested_folder_item():
    with pytest.raises(ValidationError):
        CreateFoldersRequest(
            folders=[{"parent_path": "/m", "folder_name": "x", "evil": True}]
        )
