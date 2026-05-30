"""Rate-limit contract on ``POST /api/portal/requests/batch-status``.

Infinite-scroll discover fires one batched request-status lookup per loaded
page, so an active browse bursts past the global ``120/minute`` default and
surfaced 429s. The route now carries its own ``3600/minute`` limit (per
portal-user / IP): a high ceiling that clears browsing while still bounding
abuse. This test pins the value so the decorator cannot be silently dropped
(falling back to the 120 default) or reverted.

The runtime enforcement of a per-route override is already covered behaviourally
by ``test_availability_rate_limit.py`` (same slowapi mechanism / key func), so a
fast introspection pin is enough here.
"""
from __future__ import annotations

import pytest

_BATCH_STATUS_ROUTE = "api.portal.requests.batch_status"


@pytest.mark.asyncio
async def test_batch_status_limit_is_3600_per_minute():
    import main as main_module

    limits = main_module.limiter._route_limits.get(_BATCH_STATUS_ROUTE)
    assert limits, "batch-status route has no per-route limit (fell back to the default?)"
    rate = limits[0].limit
    assert rate.amount == 3600, f"expected 3600/min, got {rate.amount}"
    assert rate.GRANULARITY.seconds == 60
