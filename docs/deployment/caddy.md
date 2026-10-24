# Deployment — Caddy (Mode B)

Caddy is the easiest TLS-terminating reverse proxy for MediaKeeper:
automatic Let's Encrypt issuance, native WebSocket forwarding, no
configuration boilerplate. The whole reverse-proxy contract fits in
four lines of `Caddyfile`.

## 1. Caddyfile

```caddy
mediakeeper.your-domain.example {
    encode gzip zstd
    reverse_proxy 127.0.0.1:8888
}
```

Caddy preserves the `Upgrade` / `Connection` headers by default, so
the chat WebSocket works without an explicit toggle. It also sets
`X-Forwarded-For`, `X-Forwarded-Proto` and `X-Forwarded-Host` by
itself; do not override them with `header_up` lines.

If Caddy and MediaKeeper run in the same Docker Compose network,
swap `127.0.0.1:8888` for the service name (`mediakeeper:8888`).

## 2. MediaKeeper environment

```dotenv
# Caddy on the host reaches the container through the Docker network
# gateway, not 127.0.0.1. Read it with `docker network inspect
# <project>_default` (Gateway field). If Caddy runs in the same
# Compose network, use the Caddy container's IP instead and pin it
# with `ipv4_address` (on a network created with a fixed subnet) so it
# survives a restart.
TRUSTED_PROXIES=172.18.0.1
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

Docker can relay other connections to a published port from that same
gateway (IPv6 visitors, and every visitor on Synology). Publish
MediaKeeper on the loopback only (`127.0.0.1:8888:8888` in the compose
file), which is all Caddy on the host needs.

With a Caddy container, drop MediaKeeper's `8888:8888` port mapping:
Caddy reaches it by its service name. Docker relays visitors to Caddy's
own ports the same way, though: they show up as the gateway, IPv6 ones
unless the network has IPv6 enabled, and all of them on Synology.
There, use DSM's reverse proxy ([synology-dsm.md](synology-dsm.md)).

## 3. Verify your setup

```bash
curl -i https://mediakeeper.your-domain.example/api/health
# → HTTP/2 200, HSTS + CSP + X-Frame-Options DENY
```

WebSocket handshake check from any chat-capable client:

```bash
# wscat is the simplest way to test from a shell.
npm i -g wscat
wscat -c "wss://mediakeeper.your-domain.example/api/portal/chat/ws/1" \
      -o https://mediakeeper.your-domain.example \
      -H "Cookie: rq_token=<a-valid-token>"
```

`Connected` means the chat WebSocket works. A 426 means the upgrade
headers did not reach MediaKeeper, a 502 that Caddy cannot reach it,
and a 403 that the origin, the token or the room was refused (room 1
exists once someone has opened the chat).

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
  settings — `TRUSTED_PROXIES` does not match the address Caddy
  connects from, or Docker relays your visitors to a Caddy container
  (section 2). Three wrong passwords would then block everyone.
