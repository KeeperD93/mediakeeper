"""Unit coverage for the CSRF cookie lifecycle helpers.

Two distinct entry points govern the ``mk_csrf`` cookie:

* :func:`ensure_csrf_cookie` is called by authenticated polls (``/me``,
  ``/refresh``). It reuses the cookie value when it matches the allowlist
  pattern, otherwise it mints a fresh token. The allowlist guards against
  cookie tampering / attribute injection while preserving the
  double-submit token across concurrent SPA requests.
* :func:`rotate_csrf_cookie` is called at auth boundaries (login,
  portal-login, change-password). It always regenerates the token,
  ignoring any pre-existing value, to close the session-fixation window.

The tests below exercise both helpers as units; the integration symmetry
contract — post-login cookie value MUST differ from a pre-supplied one —
lives in a dedicated file because it requires the API surface.
"""
from __future__ import annotations

import pytest
from fastapi import Request, Response

from api.auth._csrf import (
    CSRF_COOKIE_NAME,
    _CSRF_TOKEN_RE,
    _is_valid_csrf_token,
    ensure_csrf_cookie,
    rotate_csrf_cookie,
)


def _make_request(cookie_value: str | None = None) -> Request:
    """Build a minimal ASGI :class:`Request` carrying one cookie value."""
    headers: list[tuple[bytes, bytes]] = []
    if cookie_value is not None:
        headers.append(
            (b"cookie", f"{CSRF_COOKIE_NAME}={cookie_value}".encode("latin-1")),
        )
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


def _extract_cookie_value(response: Response) -> str | None:
    """Pick the value of the ``mk_csrf`` cookie set on ``response``."""
    for name, raw in response.raw_headers:
        if name.lower() != b"set-cookie":
            continue
        decoded = raw.decode("latin-1")
        if not decoded.startswith(f"{CSRF_COOKIE_NAME}="):
            continue
        head, _, _ = decoded.partition(";")
        _, _, value = head.partition("=")
        return value
    return None


# ensure_csrf_cookie — allowlist behaviour (polls)


def test_ensure_csrf_cookie_no_existing_generates_fresh_token():
    response = Response()
    request = _make_request()

    token = ensure_csrf_cookie(response, request)

    assert _CSRF_TOKEN_RE.fullmatch(token)
    assert _extract_cookie_value(response) == token


def test_ensure_csrf_cookie_valid_existing_is_reused():
    valid = "x" * 32
    response = Response()
    request = _make_request(cookie_value=valid)

    token = ensure_csrf_cookie(response, request)

    assert token == valid
    assert _extract_cookie_value(response) == valid


def test_ensure_csrf_cookie_too_short_is_replaced():
    response = Response()
    request = _make_request(cookie_value="abcdef")

    token = ensure_csrf_cookie(response, request)

    assert token != "abcdef"
    assert _CSRF_TOKEN_RE.fullmatch(token)


def test_ensure_csrf_cookie_too_long_is_replaced():
    overlong = "a" * 200
    response = Response()
    request = _make_request(cookie_value=overlong)

    token = ensure_csrf_cookie(response, request)

    assert token != overlong
    assert _CSRF_TOKEN_RE.fullmatch(token)


@pytest.mark.parametrize(
    "tampered",
    [
        # 32+ chars but mixing in characters outside the base64url charset
        # (each tries one of the classic cookie injection vectors).
        "a" * 32 + "!",
        "a" * 32 + " plus space",
        "a" * 32 + "%percent",
        "a" * 30 + "<>",
        "a" * 30 + '""',
    ],
)
def test_ensure_csrf_cookie_out_of_charset_is_replaced(tampered):
    response = Response()
    request = _make_request(cookie_value=tampered)

    token = ensure_csrf_cookie(response, request)

    assert token != tampered
    assert _CSRF_TOKEN_RE.fullmatch(token)


# rotate_csrf_cookie — always regenerate (auth boundaries)


def test_rotate_csrf_cookie_ignores_existing_value():
    """A valid pre-existing cookie MUST NOT be re-used at an auth boundary."""
    valid = "y" * 32
    response = Response()
    request = _make_request(cookie_value=valid)

    token = rotate_csrf_cookie(response, request)

    assert token != valid
    assert _CSRF_TOKEN_RE.fullmatch(token)
    assert _extract_cookie_value(response) == token


def test_rotate_csrf_cookie_generates_fresh_when_absent():
    response = Response()
    request = _make_request()

    token = rotate_csrf_cookie(response, request)

    assert _CSRF_TOKEN_RE.fullmatch(token)


def test_rotate_csrf_cookie_generates_unique_tokens_per_call():
    """High-entropy regeneration on every call (no stale cache)."""
    request = _make_request()

    token_a = rotate_csrf_cookie(Response(), request)
    token_b = rotate_csrf_cookie(Response(), request)

    assert token_a != token_b


# Allowlist sanity (defence in depth)


def test_allowlist_rejects_empty_string():
    assert _CSRF_TOKEN_RE.fullmatch("") is None


@pytest.mark.parametrize(
    "payload",
    [
        "a" * 32 + "; Path=/admin",
        "a" * 32 + "; HttpOnly",
        "a" * 32 + " Secure",
        "a" * 32 + "\r\nSet-Cookie: mk_token=stolen",
        "a" * 32 + "=injected",
    ],
)
def test_allowlist_rejects_attribute_injection_attempts(payload):
    assert _CSRF_TOKEN_RE.fullmatch(payload) is None


# _is_valid_csrf_token — barrier guard wrapper


def test_is_valid_csrf_token_accepts_in_window_in_charset():
    assert _is_valid_csrf_token("x" * 32) is True
    assert _is_valid_csrf_token("aBc-_" * 8) is True  # 40 chars in charset


def test_is_valid_csrf_token_rejects_empty_and_out_of_window():
    assert _is_valid_csrf_token("") is False
    assert _is_valid_csrf_token("a" * 31) is False
    assert _is_valid_csrf_token("a" * 129) is False


def test_is_valid_csrf_token_rejects_charset_violation():
    assert _is_valid_csrf_token("a" * 32 + "!") is False
    assert _is_valid_csrf_token("a" * 32 + "; Path=/x") is False
