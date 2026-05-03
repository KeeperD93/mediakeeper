"""CSP violation report endpoint.

Browsers POST here when a directive blocks a resource. Two payload
shapes are emitted in the wild:

* ``application/csp-report`` — the legacy single-report shape, still
  used by every browser that supports ``report-uri`` (Chromium-based,
  Safari, Firefox).
* ``application/reports+json`` — the modern Reporting API shape, used
  when ``report-to`` is in play. Accepted here so a future migration
  away from ``report-uri`` does not need a second deployment.

The body is logged at INFO level (rate-limited via slowapi 60/min/IP
to absorb floods of broken extensions) and the endpoint returns 204
so the browser does not retry. No DB writes — the whole pipeline is
fire-and-forget.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

from core.proxy import get_client_ip
from core.rate_limit import ip_key, limiter

router = APIRouter()
logger = logging.getLogger("mediakeeper.csp")


def _safe_decode(payload: bytes) -> dict | list | str:
    if not payload:
        return ""
    try:
        return json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return payload.decode("utf-8", errors="replace")


@router.post("/api/csp-violation-report", include_in_schema=False)
@limiter.limit("60/minute", key_func=ip_key)
async def csp_violation_report(request: Request) -> Response:
    raw_body = await request.body()
    payload = _safe_decode(raw_body)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    client = get_client_ip(request) or "unknown"
    logger.info(
        "[CSP_VIOLATION] from=%s content-type=%s payload=%s",
        client,
        content_type or "(missing)",
        payload,
    )
    return Response(status_code=204)
