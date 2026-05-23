"""Sanity + ReDoS guard tests for ``_expand_symbol_words``.

The helper expands ``&`` and ``+`` into their word-form so a search
query like ``"Lilo & Stitch"`` or ``"Naruto+Boruto"`` matches the
underlying title naturally. CodeQL flagged its ``re.sub(r"\\s*\\+\\s*",
...)`` pattern as polynomial-degree (py/polynomial-redos #144). The
rewrite uses ``str.split`` + ``str.join`` for guaranteed O(n) timing
while preserving the same effective output on well-formed inputs.

Note: the upstream caller (`GET /portal/catalog/search`) binds `q` to
`max_length=200` via FastAPI Query — the alert is not exploitable by
unauthenticated users in practice. The fix closes the class plus
removes any future-caller exposure.
"""
from __future__ import annotations

import time

from services.portal.discover_details._query_variants import _expand_symbol_words


def test_expand_basic_plus():
    assert _expand_symbol_words("Naruto+Boruto") == "Naruto Boruto"


def test_expand_plus_with_spaces():
    assert _expand_symbol_words("Naruto + Boruto") == "Naruto Boruto"


def test_expand_ampersand():
    assert _expand_symbol_words("Lilo & Stitch") == "Lilo and Stitch"


def test_expand_ampersand_and_plus_together():
    assert _expand_symbol_words("Lilo & Stitch + Frozen") == "Lilo and Stitch Frozen"


def test_expand_multiple_plus():
    assert _expand_symbol_words("a+b+c") == "a b c"


def test_expand_double_plus_collapses():
    # `++` between two words must not leave a stranded empty token.
    assert _expand_symbol_words("Naruto ++ Boruto") == "Naruto Boruto"


def test_expand_no_symbols_passthrough():
    assert _expand_symbol_words("no symbols here") == "no symbols here"


def test_expand_empty_input():
    assert _expand_symbol_words("") == ""


def test_expand_only_plus():
    assert _expand_symbol_words("+") == ""


def test_expand_collapses_multi_spaces():
    assert _expand_symbol_words("  multi   spaces  +  test  ") == "multi spaces test"


def test_expand_redos_guard_pathological_spaces():
    """100k spaces previously hung the worker (~6.4s on the old code).
    The rewrite is O(n), well under 1s."""
    pathological = " " * 100_000
    start = time.monotonic()
    result = _expand_symbol_words(pathological)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"ReDoS guard failed: {elapsed:.2f}s"
    assert result == ""
