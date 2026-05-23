"""Sanity + ReDoS guard tests for media-manager name sanitisation helpers.

Both ``_sanitize_name`` (services.media_manager._paths) and
``sanitize_filename`` (services.media_manager.naming) used to rely on
``re.sub(r'\\s*X\\s*', ...)`` patterns which CodeQL flagged as
polynomial-degree (py/polynomial-redos #143, #146). The rewrites use
``str.split`` + ``str.join`` to guarantee O(n) processing while
preserving the same effective output on well-formed inputs.

These tests pin both the semantic equivalence on typical inputs and
the ReDoS guard so a future refactor cannot silently regress either.
"""
from __future__ import annotations

import time

from services.media_manager._paths import _sanitize_name
from services.media_manager.naming import (
    build_episode_name,
    build_movie_name,
    sanitize_filename,
)


# ─────────────────────────── _sanitize_name (path-side) ───────────────────────────


def test_sanitize_name_basic_colon():
    assert _sanitize_name("Hello: World") == "Hello - World"


def test_sanitize_name_no_special_chars():
    assert _sanitize_name("plain title") == "plain title"


def test_sanitize_name_strips_forbidden_os_chars():
    assert _sanitize_name('a<b>c"d|e?f*g') == "abcdefg"


def test_sanitize_name_replaces_slashes_with_space():
    assert _sanitize_name("foo/bar\\baz") == "foo bar baz"


def test_sanitize_name_drops_commas():
    assert _sanitize_name("Foo, Bar, Baz") == "Foo Bar Baz"


def test_sanitize_name_collapses_multi_spaces():
    assert _sanitize_name("Big   Title  with   spaces") == "Big Title with spaces"


def test_sanitize_name_multiple_colons():
    assert _sanitize_name("A : B : C") == "A - B - C"


def test_sanitize_name_strips_leading_trailing():
    assert _sanitize_name("  Leading and trailing  ") == "Leading and trailing"


def test_sanitize_name_empty_input():
    assert _sanitize_name("") == ""


def test_sanitize_name_whitespace_only():
    assert _sanitize_name("   ") == ""


def test_sanitize_name_real_world_movie_title():
    # Regression anchor — actual movie title format the admin renamer hits.
    assert _sanitize_name("Star Wars: Episode IV - A New Hope") == "Star Wars - Episode IV - A New Hope"


def test_sanitize_name_redos_guard_pathological_spaces():
    """Polynomial-degree regex on pathological whitespace input must
    complete in well under 1s thanks to the ``split``/``join`` rewrite.
    Empirical measurement on the old code: 6.4s on 100k spaces."""
    pathological = " " * 100_000
    start = time.monotonic()
    result = _sanitize_name(pathological)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"ReDoS guard failed: {elapsed:.2f}s"
    assert result == ""


# ─────────────────────────── sanitize_filename (naming-side) ──────────────────────


def test_sanitize_filename_basic_colon():
    assert sanitize_filename("Title: Subtitle") == "Title - Subtitle"


def test_sanitize_filename_strips_forbidden_filesystem_chars():
    # The naming variant also forbids ``/`` and ``\\``.
    assert sanitize_filename('a/b\\c<d>e"f|g?h*i') == "abcdefghi"


def test_sanitize_filename_keeps_brackets_and_parens():
    # Brackets / parens are allowed (used by quality/year markers).
    assert sanitize_filename("Title (2026) [1080p]") == "Title (2026) [1080p]"


def test_sanitize_filename_redos_guard_pathological_spaces():
    pathological = " " * 100_000
    start = time.monotonic()
    result = sanitize_filename(pathological)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"ReDoS guard failed: {elapsed:.2f}s"
    assert result == ""


# ─────────────────────────── build_* helpers (regression anchor) ──────────────────


def test_build_movie_name_with_year_quality_ext():
    # ``sanitize_filename`` is invoked at the end — make sure the public
    # contract is preserved for the most common admin call site.
    assert build_movie_name("Inception", "2010", "1080p", ".mkv") == "Inception (2010) [1080p].mkv"


def test_build_movie_name_with_colon_in_title():
    assert build_movie_name("Star Wars: A New Hope", "1977") == "Star Wars - A New Hope (1977)"


def test_build_episode_name_basic():
    assert build_episode_name("Breaking Bad", 1, 1, "Pilot", ".mkv") == "Breaking Bad - S01E01 - Pilot.mkv"


def test_build_episode_name_with_colon_in_episode_title():
    assert build_episode_name("Demo", 1, 1, "Foo: Bar", "") == "Demo - S01E01 - Foo - Bar"
