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
        header_up X-Forwarded-For   {remote}
        header_up X-Forwarded-Host  {host}
    }
}
```

Caddy preserves the `Upgrade` / `Connection` headers by default, so
the chat WebSocket works without an explicit toggle.

If Caddy and MediaKeeper run in the same Docker Compose network,
swap `127.0.0.1:8888` for the service name (`mediakeeper:8888`).

## 2. MediaKeeper environment

```dotenv
# 127.0.0.1 because Caddy and MediaKeeper share the host loopback in
# the example above. Adjust to the Caddy container IP / CIDR if you
# run them in separate networks.
TRUSTED_PROXIES=127.0.0.1
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

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
- **Caddy in front of another proxy** (e.g., a CDN) — list every hop
  in `TRUSTED_PROXIES`; the leftmost `X-Forwarded-For` value wins so
  the upstream proxy must rewrite it correctly.
