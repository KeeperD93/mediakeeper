"""Outbound-webhook helpers shared by every notifier.

Three concerns live here, all stdlib + httpx:

* :func:`sign_webhook_payload` — HMAC-SHA256 signature of the JSON body.
  The key is derived from the existing Fernet master so no new env var
  is required. Discord ignores the header today; it is forward-compat
  for any future custom receiver and lets an operator detect MITM
  tampering during incident review.

* :func:`post_signed_with_retry` — single retry on Discord rate limits
  (HTTP 429). The ``Retry-After`` header is parsed and capped at five
  seconds to avoid blocking notification workers behind a chatty
  webhook. After the retry the result is returned to the caller, which
  is responsible for logging the final outcome.

* :func:`webhook_log_id` — non-secret identifier for log lines. Discord
  webhook URLs ship a public numeric id and a secret token; we drop
  the token entirely. Non-Discord URLs are reduced to a short SHA-256
  prefix so log files never embed a usable webhook URL.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from functools import lru_cache
from urllib.parse import urlparse

import httpx

from core.url_safety import (
    UnsafeOutboundURL,
    is_discord_webhook_url,
    validate_outbound_url,
)

#: Header name used on every outbound webhook POST.
SIGNATURE_HEADER_NAME = "X-MediaKeeper-Signature"

#: Domain-separation label for the HMAC key derivation. Bump the version
#: suffix if the derivation algorithm ever needs to change so receivers
#: can negotiate the scheme.
_SIGNING_PURPOSE = b"mediakeeper-webhook-sig-v1"

#: Maximum delay we honour from a server-side ``Retry-After`` header. A
#: misbehaving server cannot pin a notification worker for minutes.
RETRY_AFTER_CAP_SECONDS = 5.0

#: Default short backoff when ``Retry-After`` is missing or unparseable.
RETRY_AFTER_DEFAULT_SECONDS = 1.0


@lru_cache(maxsize=1)
def _master_key_bytes() -> bytes:
    """Return the bytes used as the HMAC master key.

    Resolves the persistent Fernet key when one is configured, otherwise
    falls back to a process-local random buffer so signatures are still
    well-formed in dev/test. The fallback intentionally shares its
    ephemeral lifecycle with the Fernet ephemeral key path: a restart
    invalidates both, which is consistent with "no persistent secret =
    no persistent identity" semantics.
    """
    from core.encryption import get_persistent_fernet_key

    persistent = get_persistent_fernet_key()
    if persistent is not None:
        return persistent.key.encode("ascii")
    return os.urandom(44)


@lru_cache(maxsize=1)
def _signing_key() -> bytes:
    """Return the 32-byte HMAC-SHA256 signing key derived from the master."""
    return hmac.new(
        _master_key_bytes(), _SIGNING_PURPOSE, hashlib.sha256
    ).digest()


def reset_signing_key_cache() -> None:
    """Tests only — drop the cached master and derived signing key.

    Defensive against tests that monkeypatch ``_master_key_bytes`` with
    a non-cached callable: the ``cache_clear`` attribute may be absent,
    and a missing cache to clear is a successful no-op.
    """
    for fn in (_master_key_bytes, _signing_key):
        cache_clear = getattr(fn, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()


def sign_webhook_payload(body: bytes) -> str:
    """Return ``"sha256=<hex>"`` HMAC-SHA256 of ``body``.

    ``body`` must be the exact bytes that will travel in the HTTP request
    — sign the serialised JSON, not the dict, so the receiver's
    verification matches byte-for-byte.
    """
    digest = hmac.new(_signing_key(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def webhook_log_id(url: str) -> str:
    """Return a non-secret identifier for ``url`` suitable for log lines.

    For Discord URLs the public numeric id is preserved (operators can
    correlate it with the webhook config). For anything else we emit a
    truncated SHA-256 prefix so log files never carry the live URL.

    The Discord branch piggybacks on :func:`is_discord_webhook_url` so
    bypass-style inputs (``https://discord.com@evil.com/api/webhooks/...``)
    are hashed like any other external URL rather than mislabelled
    ``discord:<id>`` in the logs.
    """
    if not url:
        return "external:unset"
    if is_discord_webhook_url(url):
        # path is ``/api/webhooks/<id>/<token>`` — index 3 is the id.
        parts = urlparse(url).path.split("/")
        if len(parts) >= 4 and parts[3].isdigit():
            return f"discord:{parts[3]}"
    return f"external:{hashlib.sha256(url.encode('utf-8')).hexdigest()[:8]}"


def parse_retry_after_header(
    value: str | None,
    *,
    cap: float = RETRY_AFTER_CAP_SECONDS,
    default: float = RETRY_AFTER_DEFAULT_SECONDS,
) -> float:
    """Parse a ``Retry-After`` header (seconds form). Returns a capped float.

    HTTP also allows an absolute date, but Discord only emits seconds.
    Anything we cannot parse falls back to ``default`` so callers always
    get a deterministic short backoff.
    """
    if not value:
        return min(default, cap)
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return min(default, cap)
    if seconds < 0:
        return 0.0
    return min(seconds, cap)


def _serialize_payload(payload: dict) -> bytes:
    """JSON-serialise ``payload`` to compact UTF-8 bytes (deterministic)."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


async def post_signed_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    *,
    timeout: float,
) -> httpx.Response:
    """POST ``payload`` to ``url`` with a signature header and a single 429 retry.

    The body is signed with :func:`sign_webhook_payload` and sent as raw
    bytes (``content=...``) so the receiver verifies the exact bytes we
    signed. On HTTP 429 the ``Retry-After`` header is honoured up to
    :data:`RETRY_AFTER_CAP_SECONDS`, then the request is replayed once.
    The caller decides what to do with the final response.

    Outbound URLs are validated up front (:func:`validate_outbound_url`)
    and the connect is DNS-pinned by the safe transport plumbed into
    :func:`core.http_client.get_external_client`. Together they refuse
    private/loopback/link-local targets and close the DNS-rebinding
    window between validation and connect (SSRF).

    The actual ``client.post`` call uses a URL whose host is a literal
    string constant — selected by an explicit ``if`` branch over the
    parsed hostname. The runtime defence chain is unchanged: this
    rebuild exists so static analysers (CodeQL ``py/full-ssrf``) see
    the hostname sanitiser at the sink rather than relying on
    interprocedural taint tracking through the
    :func:`validate_outbound_url` helper. Set-membership of a tainted
    variable is not enough — CodeQL recognises a literal in the URL
    string, so we branch and use the literal directly in each arm.

    Note: the up-front validation duplicates the DNS lookup the safe
    transport will perform on connect (~10 ms overhead per webhook).
    Kept on purpose so unsupported schemes (``http://``, ``file://``)
    are rejected before httpx tries to open the connection — they
    would otherwise reach the transport with the scheme already
    stripped.
    """
    await validate_outbound_url(url)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https":
        raise UnsafeOutboundURL("webhook_host_not_allowed")
    # Explicit branch over the (small) Discord-host whitelist so the
    # URL passed to client.post embeds a string literal — CodeQL does
    # not track set-membership constraints on tainted variables.
    if host == "discord.com":
        safe_url = f"https://discord.com{parsed.path}"
    elif host == "discordapp.com":
        safe_url = f"https://discordapp.com{parsed.path}"
    else:
        raise UnsafeOutboundURL("webhook_host_not_allowed")
    if parsed.query:
        safe_url = f"{safe_url}?{parsed.query}"
    body = _serialize_payload(payload)
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER_NAME: sign_webhook_payload(body),
    }
    res = await client.post(safe_url, content=body, headers=headers, timeout=timeout)
    if res.status_code != 429:
        return res
    delay = parse_retry_after_header(res.headers.get("Retry-After"))
    if delay > 0:
        await asyncio.sleep(delay)
    return await client.post(safe_url, content=body, headers=headers, timeout=timeout)
