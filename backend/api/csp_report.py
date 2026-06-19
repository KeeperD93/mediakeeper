"""CSP violation report endpoint.

Browsers POST here when a directive blocks a resource. Two payload
shapes are emitted in the wild:

* ``application/csp-report`` — the legacy single-report shape, still
  used by every browser that supports ``report-uri`` (Chromium-based,
  Safari, Firefox).
* ``application/reports+json`` — the modern Reporting API shape, used
  when ``report-to`` is in play. Accepted here so a future migration
  away from ``report-uri`` does not need a second deployment.

The body is read with a size cap and flattened to a single capped line
before being logged at INFO level (rate-limited via slowapi 60/min/IP
to absorb floods of broken extensions): a hostile report can neither
forge extra log lines (CR/LF injection) nor bloat the log file. The
endpoint returns 204 so the browser does not retry. No DB writes —
the whole pipeline is fire-and-forget.
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

# A CSP report is a small JSON blob; cap the buffered body so a hostile
# client cannot make the server hold an unbounded payload just to log it.
_MAX_BODY_BYTES = 16 * 1024
# Upper bound on the logged payload — keeps the log line readable and
# bounds log-file growth even within the body cap above.
_MAX_LOG_CHARS = 2000


async def _read_capped_body(request: Request) -> bytes:
    """Buffer at most ``_MAX_BODY_BYTES``, stopping early so an oversized
    body never fully materialises in memory."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        chunks.append(chunk)
        if total >= _MAX_BODY_BYTES:
            break
    return b"".join(chunks)[:_MAX_BODY_BYTES]


def _safe_decode(payload: bytes) -> dict | list | str:
    if not payload:
        return ""
    try:
        return json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return payload.decode("utf-8", errors="replace")


def _for_log(payload: dict | list | str) -> str:
    """One-line, length-capped rendering of a report body. Strips CR/LF
    so a non-JSON body cannot forge extra log lines, and truncates so a
    large body cannot bloat the log file."""
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return text.replace("\r", " ").replace("\n", " ")[:_MAX_LOG_CHARS]


@router.post("/api/csp-violation-report", include_in_schema=False)
@limiter.limit("60/minute", key_func=ip_key)
async def csp_violation_report(request: Request) -> Response:
    raw_body = await _read_capped_body(request)
    payload = _safe_decode(raw_body)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    client = get_client_ip(request) or "unknown"
    logger.info(
        "[CSP_VIOLATION] from=%s content-type=%s payload=%s",
        client,
        content_type or "(missing)",
        _for_log(payload),
    )
    return Response(status_code=204)
