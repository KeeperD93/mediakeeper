"""Unit tests for core.safe_http — DNS-pinned outbound transport."""
from __future__ import annotations

import pytest

from core.safe_http import SafeOutboundBackend, _SNIPreservingStream
from core.url_safety import UnsafeOutboundURL


class _FakeStream:
    """Minimal AsyncNetworkStream stand-in that records start_tls args."""

    def __init__(self):
        self.start_tls_calls: list[dict] = []
        self.read_calls: list[tuple[int, float | None]] = []
        self.write_calls: list[bytes] = []
        self.closed = False

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        self.start_tls_calls.append(
            {
                "ssl_context": ssl_context,
                "server_hostname": server_hostname,
                "timeout": timeout,
            }
        )
        return self

    async def read(self, max_bytes, timeout=None):
        self.read_calls.append((max_bytes, timeout))
        return b""

    async def write(self, buffer, timeout=None):
        self.write_calls.append(buffer)
        return None

    async def aclose(self):
        self.closed = True

    def get_extra_info(self, info):
        return None


class _FakeBackend:
    """Network backend stand-in capturing every connect_tcp call."""

    def __init__(self, stream: _FakeStream | None = None, fail: bool = False):
        self.connect_tcp_calls: list[dict] = []
        self.stream = stream or _FakeStream()
        self.fail = fail

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        self.connect_tcp_calls.append(
            {
                "host": host,
                "port": port,
                "timeout": timeout,
                "local_address": local_address,
            }
        )
        if self.fail:
            raise OSError("simulated_failure")
        return self.stream

    async def connect_unix_socket(self, *args, **kwargs):
        raise NotImplementedError

    async def sleep(self, seconds: float) -> None:
        return None


@pytest.mark.asyncio
async def test_backend_accepts_public_ip_literal():
    base = _FakeBackend()
    backend = SafeOutboundBackend(base=base)
    stream = await backend.connect_tcp("8.8.8.8", 443)
    assert isinstance(stream, _SNIPreservingStream)
    assert len(base.connect_tcp_calls) == 1
    assert base.connect_tcp_calls[0]["host"] == "8.8.8.8"


@pytest.mark.asyncio
async def test_backend_rejects_private_ipv4_literal():
    base = _FakeBackend()
    backend = SafeOutboundBackend(base=base)
    with pytest.raises(UnsafeOutboundURL) as exc:
        await backend.connect_tcp("192.168.1.10", 443)
    assert exc.value.reason == "private_ip_literal"
    assert base.connect_tcp_calls == []


@pytest.mark.asyncio
async def test_backend_rejects_loopback_literal():
    base = _FakeBackend()
    backend = SafeOutboundBackend(base=base)
    with pytest.raises(UnsafeOutboundURL):
        await backend.connect_tcp("127.0.0.1", 443)
    assert base.connect_tcp_calls == []


@pytest.mark.asyncio
async def test_backend_resolves_hostname_and_connects_to_validated_ip(monkeypatch):
    async def _resolve(_host):
        return ["8.8.8.8", "1.1.1.1"]

    monkeypatch.setattr("core.safe_http.resolve_host", _resolve)
    base = _FakeBackend()
    backend = SafeOutboundBackend(base=base)
    stream = await backend.connect_tcp("dns.example", 443)
    assert isinstance(stream, _SNIPreservingStream)
    # The base backend MUST be invoked with the resolved IP, not the
    # hostname — that is what closes the DNS rebinding window.
    assert base.connect_tcp_calls[0]["host"] == "8.8.8.8"


@pytest.mark.asyncio
async def test_backend_rejects_hostname_resolving_to_private(monkeypatch):
    async def _resolve(_host):
        return ["192.168.1.1"]

    monkeypatch.setattr("core.safe_http.resolve_host", _resolve)
    base = _FakeBackend()
    backend = SafeOutboundBackend(base=base)
    with pytest.raises(UnsafeOutboundURL) as exc:
        await backend.connect_tcp("rebinder.example", 443)
    assert exc.value.reason == "dns_resolves_private"
    assert base.connect_tcp_calls == []


@pytest.mark.asyncio
async def test_backend_rejects_when_any_record_is_private(monkeypatch):
    """A single private answer in the DNS reply poisons the whole set."""

    async def _resolve(_host):
        return ["8.8.8.8", "10.0.0.5"]

    monkeypatch.setattr("core.safe_http.resolve_host", _resolve)
    base = _FakeBackend()
    backend = SafeOutboundBackend(base=base)
    with pytest.raises(UnsafeOutboundURL) as exc:
        await backend.connect_tcp("partially.evil.example", 443)
    assert exc.value.reason == "dns_resolves_private"


@pytest.mark.asyncio
async def test_backend_falls_back_to_next_ip_on_connect_failure(monkeypatch):
    async def _resolve(_host):
        return ["8.8.8.8", "1.1.1.1"]

    monkeypatch.setattr("core.safe_http.resolve_host", _resolve)

    attempts: list[str] = []
    backup_stream = _FakeStream()

    class _PartialFail:
        async def connect_tcp(self, host, port, **kwargs):
            attempts.append(host)
            if host == "8.8.8.8":
                raise OSError("first_ip_down")
            return backup_stream

        async def connect_unix_socket(self, *a, **k):
            raise NotImplementedError

        async def sleep(self, _s):
            return None

    backend = SafeOutboundBackend(base=_PartialFail())
    stream = await backend.connect_tcp("flaky.example", 443)
    assert isinstance(stream, _SNIPreservingStream)
    assert attempts == ["8.8.8.8", "1.1.1.1"]


@pytest.mark.asyncio
async def test_backend_raises_when_dns_fails(monkeypatch):
    async def _resolve(_host):
        return []

    monkeypatch.setattr("core.safe_http.resolve_host", _resolve)
    base = _FakeBackend()
    backend = SafeOutboundBackend(base=base)
    with pytest.raises(UnsafeOutboundURL) as exc:
        await backend.connect_tcp("nx.invalid", 443)
    assert exc.value.reason == "dns_resolution_failed"


@pytest.mark.asyncio
async def test_backend_refuses_unix_socket():
    backend = SafeOutboundBackend(base=_FakeBackend())
    with pytest.raises(UnsafeOutboundURL) as exc:
        await backend.connect_unix_socket("/tmp/sock")
    assert exc.value.reason == "unix_socket_not_allowed"


@pytest.mark.asyncio
async def test_sni_stream_forces_original_host_on_start_tls():
    """``start_tls`` MUST pass the original hostname, even if the caller
    overrides ``server_hostname`` to the IP literal we connected to."""
    base_stream = _FakeStream()
    wrapped = _SNIPreservingStream(base_stream, original_host="discord.com")
    result = await wrapped.start_tls(ssl_context="fake_ctx", server_hostname="8.8.8.8")
    assert len(base_stream.start_tls_calls) == 1
    assert base_stream.start_tls_calls[0]["server_hostname"] == "discord.com"
    assert isinstance(result, _SNIPreservingStream)


@pytest.mark.asyncio
async def test_sni_stream_delegates_io_methods():
    base_stream = _FakeStream()
    wrapped = _SNIPreservingStream(base_stream, original_host="example.com")
    await wrapped.write(b"payload")
    await wrapped.read(1024, timeout=5.0)
    await wrapped.aclose()
    assert base_stream.write_calls == [b"payload"]
    assert base_stream.read_calls == [(1024, 5.0)]
    assert base_stream.closed is True
