"""The trim of a submitted display name: every space and the byte-order mark leave
both edges, other invisible characters stay for the rules to refuse, and a long run
of spaces does not stall it.

Spaces and invisible characters are spelled as code points, never as themselves."""
import time

import pytest

from constants import display_name as dn
from services.portal.display_name_rules import clean_display_name

BOM = chr(0xFEFF)
# Every character str.isspace() accepts, then the byte-order mark.
EDGE_CODE_POINTS = (
    *range(0x09, 0x0E), *range(0x1C, 0x21), 0x85, 0xA0, 0x1680,
    *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF,
)


@pytest.mark.parametrize("code_point", EDGE_CODE_POINTS)
def test_every_space_and_the_byte_order_mark_leave_both_edges(code_point):
    # The marks outside keep the clip's own strip() from doing the trim's work.
    edge = chr(code_point)
    assert clean_display_name(BOM + edge + "Bob" + edge + BOM) == "Bob"


@pytest.mark.parametrize("code_point", [0x180E, 0x200B, 0x2060])
def test_invisible_characters_that_are_not_spaces_stay_for_the_rules(code_point):
    hidden = chr(code_point)
    assert clean_display_name(hidden + "Bob" + hidden) == hidden + "Bob" + hidden


def test_mixed_spaces_and_byte_order_marks_leave_the_edges_not_the_inside():
    nbsp, wide = chr(0x00A0), chr(0x3000)
    name = BOM + " " + wide + BOM + "Bob" + nbsp + "by" + nbsp + BOM + chr(0x2028)
    assert clean_display_name(name) == "Bob" + nbsp + "by"
    assert clean_display_name(BOM + " " + BOM) == ""


def test_a_long_run_of_spaces_inside_a_name_does_not_stall_the_trim(monkeypatch):
    # The routes and the clip cap names at 50 characters. Past that cap, a pattern
    # anchored to the end took seconds on such a run; the scan takes milliseconds.
    monkeypatch.setattr(dn, "MAX_LENGTH", 200_000)
    inner = "Bob" + " " * 50_000 + "by"
    edges = (BOM + " ") * 25_000 + "Bobby" + (chr(0x3000) + BOM) * 25_000
    started = time.perf_counter()
    assert clean_display_name(inner) == inner
    assert clean_display_name(edges) == "Bobby"
    assert time.perf_counter() - started < 1.0
