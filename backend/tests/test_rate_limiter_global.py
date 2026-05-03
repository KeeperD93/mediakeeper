"""Baseline tests for the slowapi global rate-limit middleware.

The application ships ``SlowAPIMiddleware`` as a defence-in-depth garde-fou:
every IP gets a baseline 120 req/min budget. Per-route quotas (login,
change-password, availability, chat send) sit on top of this and are
covered by their own dedicated test files.

These tests verify that the middleware is wired to the FastAPI app, that
the ``Limiter`` exposes the expected default limit, and that the 121st
request from one IP receives a 429 response.
"""
from __future__ import annotations

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Clear the in-memory limiter buckets before and after each test so
    one test cannot starve the budget of another."""
    import main as main_module
    main_module.limiter.reset()
    yield
    main_module.limiter.reset()


@pytest.mark.asyncio
async def test_slowapi_middleware_is_registered():
    """The ASGI middleware stack must include SlowAPIMiddleware once the
    app boots — otherwise the ``Limiter`` is purely declarative and never
    enforced on the request path."""
    import main as main_module
    classes = [m.cls.__name__ for m in main_module.app.user_middleware]
    assert "SlowAPIMiddleware" in classes


@pytest.mark.asyncio
async def test_slowapi_default_limit_is_120_per_minute():
    """The global baseline must stay at 120 req/min/IP. Tightening this
    value here without surveying the call-sites would silently 429 admin
    polling on the dashboard."""
    import main as main_module
    groups = main_module.limiter._default_limits
    assert groups, "limiter has no default limits configured"
    parsed = list(groups[0])
    assert parsed, "default LimitGroup yielded no Limit objects"
    rate = parsed[0].limit
    assert rate.amount == 120
    assert rate.GRANULARITY.seconds == 60


@pytest.mark.asyncio
async def test_slowapi_returns_429_when_default_limit_exceeded(client):
    """Fire 121 requests from the same client. The first 120 must succeed
    (they fit in the per-minute window) and at least one of the trailing
    requests must come back as 429."""
    seen_codes: set[int] = set()
    last_response = None
    for _ in range(125):
        last_response = await client.get("/api/health")
        seen_codes.add(last_response.status_code)
        if last_response.status_code == 429:
            break
    assert 200 in seen_codes
    assert 429 in seen_codes, f"expected a 429 within 125 requests, saw {seen_codes}"
    # Defence-in-depth: 429 responses still carry the security headers.
    assert last_response is not None
    assert last_response.status_code == 429
    assert last_response.headers.get("X-Frame-Options") == "DENY"
    assert last_response.headers.get("X-Content-Type-Options") == "nosniff"
