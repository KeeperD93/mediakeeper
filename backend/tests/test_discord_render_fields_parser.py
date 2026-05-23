"""Sanity + ReDoS guard tests for ``_parse_fields``.

The helper extracts ``<fields>[...]</fields>`` JSON blocks from Discord
embed templates so admins can declare custom embed fields inline.
CodeQL flagged the previous ``re.search(r"<fields>(.*?)</fields>",
..., re.DOTALL)`` as polynomial-degree (py/polynomial-redos #145).
The rewrite uses ``str.find`` for guaranteed O(n) processing.

Note: the upstream caller (``POST /api/notifications/discord/test``)
is admin-authenticated and the template originates from admin-edited
``wh_config`` (or built-in defaults). The alert was not exploitable
by unauthenticated users.
"""
from __future__ import annotations

import time

from services.discord._render import _parse_fields


# ─────────────────────────── nominal extraction ───────────────────────────


def test_parse_fields_extracts_single_block():
    tmpl = 'foo<fields>[{"name":"N","value":"V"}]</fields>bar'
    text, fields = _parse_fields(tmpl)
    assert text == "foobar"
    assert fields == [{"name": "N", "value": "V"}]


def test_parse_fields_extracts_with_dotall_content():
    tmpl = 'multi\nline\n<fields>\n[1,2]\n</fields>\nrest'
    text, fields = _parse_fields(tmpl)
    assert text == "multi\nline\n\nrest"
    assert fields == [1, 2]


def test_parse_fields_handles_empty_array():
    text, fields = _parse_fields("<fields>[]</fields>")
    assert text == ""
    assert fields == []


def test_parse_fields_handles_empty_body():
    # `json.loads("")` raises -> caught, fields stays default [].
    text, fields = _parse_fields("<fields></fields>")
    assert text == ""
    assert fields == []


def test_parse_fields_processes_only_first_block():
    """Two consecutive blocks: only the first is consumed (preserves
    previous `re.search` semantics)."""
    tmpl = "<fields>[1]</fields><fields>[2]</fields>"
    text, fields = _parse_fields(tmpl)
    assert text == "<fields>[2]</fields>"
    assert fields == [1]


# ─────────────────────────── degenerate inputs ────────────────────────────


def test_parse_fields_no_marker_passthrough():
    text, fields = _parse_fields("no fields tag")
    assert text == "no fields tag"
    assert fields == []


def test_parse_fields_unclosed_marker_passthrough():
    text, fields = _parse_fields("<fields>abc")
    assert text == "<fields>abc"
    assert fields == []


def test_parse_fields_close_only_passthrough():
    text, fields = _parse_fields("abc</fields>")
    assert text == "abc</fields>"
    assert fields == []


def test_parse_fields_invalid_json_kept_as_default():
    text, fields = _parse_fields("<fields>invalid json</fields>")
    assert text == ""
    assert fields == []


def test_parse_fields_empty_template():
    assert _parse_fields("") == ("", [])


def test_parse_fields_strips_outer_whitespace():
    text, fields = _parse_fields('  <fields>[{"x":1}]</fields>  ')
    assert text == ""
    assert fields == [{"x": 1}]


# ─────────────────────────── ReDoS guard ──────────────────────────────────


def test_parse_fields_redos_guard_unclosed_long_input():
    """Pathological input: `<fields>` followed by 100k chars and no
    closing marker. The rewrite is O(n) garanti (two `str.find` calls),
    well under 1s."""
    pathological = "<fields>" + "a" * 100_000
    start = time.monotonic()
    text, fields = _parse_fields(pathological)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"ReDoS guard failed: {elapsed:.2f}s"
    assert text == pathological  # no match -> input unchanged (modulo strip)
    assert fields == []
