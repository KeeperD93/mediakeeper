"""_hex_to_int color conversion guards for the Discord embed color."""
from __future__ import annotations

from services.discord._render import _hex_to_int

_DEFAULT_GREEN = 3066993


def test_hex_to_int_accepts_plain_int():
    assert _hex_to_int(5763719) == 5763719


def test_hex_to_int_parses_hex_string():
    assert _hex_to_int("#FF0000") == 0xFF0000


def test_hex_to_int_bool_falls_back_to_default():
    # bool is an int subclass; a stray `color: true`/`false` in an admin
    # config must not render as 1/0 but fall back to the default color.
    assert _hex_to_int(True) == _DEFAULT_GREEN
    assert _hex_to_int(False) == _DEFAULT_GREEN


def test_hex_to_int_none_and_garbage_fall_back():
    assert _hex_to_int(None) == _DEFAULT_GREEN
    assert _hex_to_int("not-a-color") == _DEFAULT_GREEN
