"""DNS-pinned httpx transport that closes the SSRF rebinding window.

:func:`core.url_safety.validate_outbound_url` resolves the destination
hostname and rejects it when any answer points inside the LAN. That
covers misconfigured webhook URLs and naive attacker payloads but
leaves a TOCTOU window: between the validation lookup and the actual
httpx connect a malicious authoritative DNS server can flip the
``A`` record to ``192.168.x.x`` (the classic DNS-rebinding attack).

This module closes that window by:

* sub-classing :class:`httpcore.AsyncNetworkBackend` so we own DNS
  resolution + validation **inside** the connect path,
* connecting to a validated IP literal instead of the hostname (the
  backend cannot re-resolve and land on a private answer mid-connect),
* preserving the original hostname for TLS SNI and certificate
  verification through a stream wrapper that forces
  ``server_hostname=<original>`` on :meth:`start_tls`.

The transport is plumbed into :func:`core.http_client.get_external_client`
so every external-facing request goes through it (TMDB, OpenSubtitles,
Discord webhooks). Internal calls (``_internal_client``) keep the
default backend so they can still reach the NAS at ``192.168.x.x``.
"""
from __future__ import annotations

import socket
from typing import Iterable

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend

from core.url_safety import UnsafeOutboundURL, is_private_address, resolve_host


class _SNIPreservingStream(httpcore.AsyncNetworkStream):
    """Force TLS SNI/cert hostname to the originally requested name.

    We connect to an IP literal (so the kernel resolves nothing under
    us) but TLS still needs to present the original hostname so the
    handshake matches the server certificate.
    """

    def __init__(
        self,
        base: httpcore.AsyncNetworkStream,
        *,
        original_host: str,
    ) -> None:
        self._base = base
        self._original_host = original_host

    async def start_tls(
        self,
        ssl_context,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.AsyncNetworkStream:
        wrapped = await self._base.start_tls(
            ssl_context,
            server_hostname=self._original_host,
            timeout=timeout,
        )
        return _SNIPreservingStream(wrapped, original_host=self._original_host)

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return await self._base.read(max_bytes, timeout)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        await self._base.write(buffer, timeout)

    async def aclose(self) -> None:
        await self._base.aclose()

    def get_extra_info(self, info: str):
        return self._base.get_extra_info(info)


class SafeOutboundBackend(httpcore.AsyncNetworkBackend):
    """Resolve + validate the host inside ``connect_tcp``.

    Wraps a base backend (``AutoBackend`` in production, a fake in
    tests). For every connect_tcp call:

    1. Skip validation when the host is already an IP literal in the
       allowed set — the caller has obviously bypassed DNS on purpose.
       Reject IP literals in the private set outright.
    2. Otherwise resolve the hostname and reject if any answer is
       private. The check is performed *here*, immediately before the
       connect, so DNS rebinding between an earlier check and now is
       caught.
    3. Connect to the first validated IP. The hostname is preserved
       for SNI through the returned :class:`_SNIPreservingStream`.
    """

    def __init__(self, base: httpcore.AsyncNetworkBackend | None = None) -> None:
        self._base = base or AutoBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        normalized_host = (host or "").lower().rstrip(".")
        # IP literal path — accept public IPs, reject private outright.
        if _looks_like_ip_literal(normalized_host):
            if is_private_address(normalized_host):
                raise UnsafeOutboundURL("private_ip_literal")
            stream = await self._base.connect_tcp(
                normalized_host,
                port,
                timeout=timeout,
                local_address=local_address,
                socket_options=socket_options,
            )
            return _SNIPreservingStream(stream, original_host=normalized_host)

        # Hostname path — resolve + validate every answer + connect to
        # the first safe IP. Any private answer poisons the whole set
        # (single record is enough to detect a rebinding attempt).
        addrs = await resolve_host(normalized_host)
        if not addrs:
            raise UnsafeOutboundURL("dns_resolution_failed")
        for addr in addrs:
            if is_private_address(addr):
                raise UnsafeOutboundURL("dns_resolves_private")
        last_err: OSError | None = None
        for ip in addrs:
            try:
                stream = await self._base.connect_tcp(
                    ip,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except OSError as e:
                last_err = e
                continue
            return _SNIPreservingStream(stream, original_host=normalized_host)
        raise last_err if last_err is not None else OSError("connect_failed")

    async def connect_unix_socket(self, *args, **kwargs):
        # No outbound caller hits a Unix socket. Refuse explicitly so a
        # future regression does not silently fall through to the base.
        raise UnsafeOutboundURL("unix_socket_not_allowed")

    async def sleep(self, seconds: float) -> None:
        await self._base.sleep(seconds)


def _looks_like_ip_literal(host: str) -> bool:
    """Return ``True`` if ``host`` parses as an IPv4 or IPv6 literal."""
    try:
        socket.inet_pton(socket.AF_INET, host)
        return True
    except OSError:
        pass
    # Strip ``[`` / ``]`` so we accept the bracketed form from URLs.
    stripped = host.strip("[]")
    try:
        socket.inet_pton(socket.AF_INET6, stripped)
        return True
    except OSError:
        return False


def make_safe_external_transport(
    *,
    verify: bool | str = True,
    http2: bool = False,
) -> httpx.AsyncBaseTransport:
    """Return an :class:`httpx.AsyncHTTPTransport` wired to the safe backend.

    Construction mirrors the httpx default transport so it can be a
    drop-in replacement in :mod:`core.http_client`. ``verify`` stays
    overridable because the regular external client already exposed
    that knob.
    """
    transport = httpx.AsyncHTTPTransport(verify=verify, http2=http2)
    # httpx 0.28's ``AsyncHTTPTransport`` keeps the pool on ``_pool``.
    # Swap its network backend in place; the public API does not yet
    # accept a backend parameter directly.
    pool: httpcore.AsyncConnectionPool = transport._pool  # type: ignore[attr-defined]
    pool._network_backend = SafeOutboundBackend()
    return transport
