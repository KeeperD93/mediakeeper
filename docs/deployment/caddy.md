# Deployment — Caddy (Mode B)

Caddy is the easiest TLS-terminating reverse proxy for MediaKeeper:
automatic Let's Encrypt issuance, native WebSocket forwarding, no
configuration boilerplate. The whole reverse-proxy contract fits in
six lines of `Caddyfile`.

## 1. Caddyfile

```caddy
mediakeeper.your-domain.example {
    encode gzip zstd

    reverse_proxy 127.0.0.1:8888 {
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-Host  {host}
    }
}
```

Caddy preserves the `Upgrade` / `Connection` headers by default, so
the chat WebSocket works without an explicit toggle. It also sets
`X-Forwarded-For` to the visitor's address by itself; do not override
it with a `header_up` line.

If Caddy and MediaKeeper run in the same Docker Compose network,
swap `127.0.0.1:8888` for the service name (`mediakeeper:8888`).

## 2. MediaKeeper environment

```dotenv
# Caddy on the host reaches the container through the Docker network
# gateway, not 127.0.0.1. Read it with `docker network inspect
# <project>_default` (Gateway field). If Caddy runs in the same
# Compose network, use the Caddy container's IP instead.
TRUSTED_PROXIES=172.18.0.1
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

Docker relays some connections to a published port (IPv6 visitors)
from that same gateway. Publish MediaKeeper on the loopback only
(`127.0.0.1:8888:8888` in the compose file), which is all Caddy needs.

## 3. Verify your setup

```bash
curl -I https://mediakeeper.your-domain.example/api/health
# → HTTP/2 200, HSTS + CSP + X-Frame-Options DENY
```

WebSocket handshake check from any chat-capable client:

```bash
# wscat is the simplest way to test from a shell.
npm i -g wscat
wscat -c "wss://mediakeeper.your-domain.example/api/portal/chat/ws/1" \
      -H "Cookie: rq_token=<a-valid-token>"
```

A 426 in the curl output (or a connection refused on the wscat call)
means the upstream is not actually MediaKeeper or the Caddy `reverse_proxy`
directive is misconfigured.

## 4. Common pitfalls

- **Wildcard hostname** (`*.your-domain.example`) — works, but pin
  `FRONTEND_ORIGIN` to the exact subdomain you publish or the chat WS
  guard rejects valid handshakes.
- **HTTP/3 enabled** — fine, MediaKeeper does not depend on the
  underlying transport version.
- **Caddy behind a CDN** — add the CDN's address ranges to Caddy's
  global `servers { trusted_proxies static … }` option, so Caddy keeps
  the CDN's `X-Forwarded-For` and appends to it, then list the same
  ranges in `TRUSTED_PROXIES`. MediaKeeper reads the header from the
  right and keeps the first address that is not a listed proxy.
- **Every visitor shows the same address** in the Security tab of the
  settings → `TRUSTED_PROXIES` does not match the address Caddy
  connects from. Three wrong passwords would then block everyone.
