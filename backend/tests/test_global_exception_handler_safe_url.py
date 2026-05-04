"""Verify that the global exception handler uses :func:`safe_request_url`.

A query-string parameter such as ``?token=foo`` must not appear in the
error log emitted when the global handler reports an unhandled
exception. We invoke the handler directly with a synthetic Starlette
``Request`` so the test does not depend on the ASGI transport's
exception-propagation policy.
"""
import logging

import pytest
from starlette.requests import Request

import main as main_module


def _make_request(path: str, query: bytes) -> Request:
    return Request(
        scope={
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query,
            "headers": [],
            "scheme": "http",
            "server": ("test", 80),
            "client": ("127.0.0.1", 0),
            "root_path": "",
            "http_version": "1.1",
            "asgi": {"version": "3.0"},
        }
    )


@pytest.mark.asyncio
async def test_global_handler_strips_query_from_log(caplog):
    request = _make_request(
        "/api/test/explode", b"token=should-not-be-logged&next=/home"
    )

    with caplog.at_level(logging.ERROR, logger="mediakeeper"):
        response = await main_module.global_exception_handler(
            request, RuntimeError("intentional failure")
        )

    assert response.status_code == 500
    error_lines = [
        r.getMessage() for r in caplog.records
        if "Unhandled error" in r.getMessage()
    ]
    assert error_lines, "expected an Unhandled error line"
    rendered = "\n".join(error_lines)
    assert "/api/test/explode" in rendered
    assert "token=" not in rendered
    assert "should-not-be-logged" not in rendered


@pytest.mark.asyncio
async def test_global_handler_keeps_path_visible(caplog):
    """The path itself must remain in the log so an operator can locate
    the failing route — only the query string is dropped."""
    request = _make_request("/api/foo/bar", b"safe=value")

    with caplog.at_level(logging.ERROR, logger="mediakeeper"):
        await main_module.global_exception_handler(
            request, RuntimeError("boom")
        )

    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert "/api/foo/bar" in rendered
    assert "safe=value" not in rendered
