"""Sanity + ReDoS guard tests for ``services.portal.strip_tags_and_trim``.

The helper is used 22 times across the portal (chat, news, lists,
tickets, events, social, profiles…) to clean user-supplied strings
before they hit the database. CodeQL flagged its internal regex
``<[^>]+>`` as polynomial-degree (CodeQL #142, py/polynomial-redos)
because unmatched ``<`` repetitions trigger O(n²) backtracking.

The fix in ``services.portal.__init__`` bounds the input before the
regex runs (defense in depth — independent of upstream Pydantic
``max_length`` guards). These tests pin the fix in place so a future
refactor cannot silently regress it.
"""
from __future__ import annotations

import time

from services.portal import strip_tags_and_trim


def test_strips_naked_html_tags():
    assert strip_tags_and_trim("<b>hello</b>") == "hello"


def test_preserves_plain_text():
    assert strip_tags_and_trim("hello world") == "hello world"


def test_returns_empty_on_empty_input():
    assert strip_tags_and_trim("") == ""


def test_returns_empty_on_none_input():
    assert strip_tags_and_trim(None) == ""  # type: ignore[arg-type]


def test_respects_max_len_on_plain_text():
    assert strip_tags_and_trim("a" * 100, max_len=10) == "a" * 10


def test_strips_then_clamps():
    # 20 ``a`` after tag strip, max_len=5 ⇒ output is 5 ``a``.
    assert strip_tags_and_trim("<i>" + "a" * 20 + "</i>", max_len=5) == "a" * 5


def test_redos_guard_under_pathological_input():
    """Polynomial-degree regex on pathological ``<`` input must complete
    well under 1s thanks to the internal ``len(text) > max_len`` cap.

    Without the cap (regression scenario), 100k chars of ``<`` would
    spin the engine on O(n²) ≈ 10^10 ops, blocking the worker. With the
    cap, only the first ``max_len`` characters reach the regex.
    """
    pathological = "<" * 100_000
    start = time.monotonic()
    result = strip_tags_and_trim(pathological, max_len=2000)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"ReDoS guard failed: {elapsed:.2f}s"
    # No closing ``>`` anywhere → regex matches nothing → output is the
    # truncated raw text.
    assert result == "<" * 2000
