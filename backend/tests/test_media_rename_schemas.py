"""Schema-level guards on the admin rename endpoints.

The four Pydantic models exposed by ``api.media._rename`` now reject
extra fields (``ConfigDict(extra="forbid")``) and enforce explicit
``max_length`` bounds on every string field. This is defence in depth
behind the polynomial-degree sanitisation regexes that were rewritten
in the same cycle: even with a degenerate regex, a payload that
exceeds the schema bound never reaches the helper.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.media._rename import (
    EpisodeNameRequest,
    MovieNameRequest,
    RenameBatchRequest,
    RenameFolderRequest,
    RenameRequest,
    _MAX_NAME_LEN,
    _MAX_PATH_LEN,
    _MAX_TITLE_LEN,
)


# ─────────────────────────── RenameRequest ────────────────────────────────


def test_rename_request_accepts_typical_payload():
    req = RenameRequest(old_path="/data/medias/old.mkv", new_name="new.mkv")
    assert req.old_path == "/data/medias/old.mkv"
    assert req.new_name == "new.mkv"


def test_rename_request_rejects_extra_field():
    with pytest.raises(ValidationError):
        RenameRequest(old_path="/x", new_name="y", malicious="field")


def test_rename_request_rejects_oversized_path():
    with pytest.raises(ValidationError):
        RenameRequest(old_path="x" * (_MAX_PATH_LEN + 1), new_name="ok.mkv")


def test_rename_request_rejects_oversized_name():
    with pytest.raises(ValidationError):
        RenameRequest(old_path="/data", new_name="x" * (_MAX_NAME_LEN + 1))


def test_rename_request_rejects_empty_new_name():
    with pytest.raises(ValidationError):
        RenameRequest(old_path="/data", new_name="")


# ─────────────────────────── RenameBatchRequest ───────────────────────────


def test_rename_batch_request_accepts_small_batch():
    req = RenameBatchRequest(items=[RenameRequest(old_path="/a", new_name="b")])
    assert len(req.items) == 1
    assert req.cat == ""


def test_rename_batch_request_caps_item_count():
    too_many = [{"old_path": "/x", "new_name": "y"}] * 501
    with pytest.raises(ValidationError):
        RenameBatchRequest(items=too_many)


def test_rename_batch_request_rejects_extra_field():
    with pytest.raises(ValidationError):
        RenameBatchRequest(items=[], cat="films", unexpected=True)


# ─────────────────────────── MovieNameRequest ─────────────────────────────


def test_movie_name_request_accepts_typical_payload():
    req = MovieNameRequest(title="Inception", year="2010", quality="1080p", ext=".mkv")
    assert req.title == "Inception"


def test_movie_name_request_rejects_oversized_title():
    with pytest.raises(ValidationError):
        MovieNameRequest(title="x" * (_MAX_TITLE_LEN + 1), year="2010")


def test_movie_name_request_rejects_empty_title():
    with pytest.raises(ValidationError):
        MovieNameRequest(title="", year="2010")


def test_movie_name_request_rejects_extra_field():
    with pytest.raises(ValidationError):
        MovieNameRequest(title="ok", year="2010", malicious="field")


# ─────────────────────────── EpisodeNameRequest ───────────────────────────


def test_episode_name_request_accepts_typical_payload():
    req = EpisodeNameRequest(series="Demo", season=1, episode=1, title="Pilot", ext=".mkv")
    assert req.episode == 1


def test_episode_name_request_rejects_negative_season():
    with pytest.raises(ValidationError):
        EpisodeNameRequest(series="Demo", season=-1, episode=1, title="Pilot")


def test_episode_name_request_caps_extreme_season():
    with pytest.raises(ValidationError):
        EpisodeNameRequest(series="Demo", season=1000, episode=1, title="Pilot")


def test_episode_name_request_caps_extreme_episode():
    with pytest.raises(ValidationError):
        EpisodeNameRequest(series="Demo", season=1, episode=10000, title="Pilot")


def test_episode_name_request_rejects_extra_field():
    with pytest.raises(ValidationError):
        EpisodeNameRequest(series="Demo", season=1, episode=1, title="Pilot", evil=True)


# ─────────────────────────── RenameFolderRequest ──────────────────────────


def test_rename_folder_request_accepts_typical_payload():
    req = RenameFolderRequest(cat="films", subpath="Action/Inception", new_name="Inception (2010)")
    assert req.new_name == "Inception (2010)"


def test_rename_folder_request_rejects_oversized_subpath():
    with pytest.raises(ValidationError):
        RenameFolderRequest(cat="films", subpath="x" * (_MAX_PATH_LEN + 1), new_name="ok")


def test_rename_folder_request_rejects_empty_new_name():
    with pytest.raises(ValidationError):
        RenameFolderRequest(cat="films", subpath="x", new_name="")


def test_rename_folder_request_rejects_extra_field():
    with pytest.raises(ValidationError):
        RenameFolderRequest(cat="films", subpath="x", new_name="y", evil=True)
