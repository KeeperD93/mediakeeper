# Deployment — Synology DSM Reverse Proxy (Mode B)

DSM ships with a reverse-proxy UI under
**Control Panel → Login Portal → Advanced → Reverse Proxy**. It can
terminate TLS, forward to the MediaKeeper container, and proxy the
chat WebSocket — all without leaving the web UI.

## 1. Reverse-proxy entry

Create a new entry pointing at the container:

| Field | Value |
|---|---|
| Source — Protocol | HTTPS |
| Source — Hostname | `mediakeeper.your-domain.example` |
| Source — Port | 443 |
| Destination — Protocol | HTTP |
| Destination — Hostname | `localhost` (or container hostname) |
| Destination — Port | 8888 |

In the **Custom Header** tab, append three rows so MediaKeeper sees
the real client metadata:

```
X-Forwarded-Host   $host
X-Forwarded-Proto  https
X-Forwarded-For    $remote_addr
```

In the **WebSocket** tab, tick **Enable WebSocket**. Without this DSM
strips the Upgrade header and the chat handshake degrades into a 426
response (visible in MediaKeeper logs as
`received an HTTP GET on the chat WebSocket path`).

DSM 7.2+ also honours HTTP/2 in this same tab — leave it on for
better Vue bundle delivery.

## 2. MediaKeeper environment

Drop these lines in `/etc/mediakeeper.env`:

```dotenv
# DSM listens on 192.0.2.10 in this example, replace with the LAN IP
# of your NAS as seen from the container's network namespace.
TRUSTED_PROXIES=192.0.2.10
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

`TRUSTED_PROXIES` is what unlocks `X-Forwarded-*` honouring;
`FRONTEND_ORIGIN` switches the chat WS guard from auto-derive to a
strict allowlist; `COOKIE_SECURE=true` is redundant once HTTPS is
detected, but explicit is better when DSM ever swaps to a non-stable
intermediate hop.

If pinning a single DSM IP is awkward (DHCP, dual-stack, multiple
NAS), a private LAN range works as a safe wider default:

```dotenv
TRUSTED_PROXIES=192.168.0.0/16
```

Trade-off: any host on the same LAN that can reach port `8888`
directly will then have its `X-Forwarded-Host` honoured — fine for a
home network, less appropriate for a co-tenanted VLAN. Pin the exact
proxy IP when the LAN is shared with untrusted hosts.

If MediaKeeper boots with `TRUSTED_PROXIES` set but `FRONTEND_ORIGIN`
left empty, you will see this WARN once at startup — set the public
origin to silence it:

```
[startup] FRONTEND_ORIGIN is unset while TRUSTED_PROXIES is configured
(reverse-proxy mode). CORS preflights from the public origin will be
rejected until FRONTEND_ORIGIN is set to the public URL …
```

Restart the container so the new env takes effect.

### Persistent encryption key

Set `MEDIAKEEPER_ENCRYPTION_KEY` (any 32-byte url-safe base64 value)
**before the first `docker compose up`** so every encrypted secret
written from then on (Discord webhooks, Imgur secret, Emby tokens…)
survives a container restart:

```dotenv
# Generate once and keep safe — losing it makes encrypted DB rows unreadable.
MEDIAKEEPER_ENCRYPTION_KEY=<paste your fernet key here>
```

If neither the env var nor `/data/.encryption_key` is provided,
MediaKeeper falls back to a process-local key. The admin UI shows a
persistent red banner on every page until the key is made persistent;
the same condition is exposed at `GET /api/health/encryption`
(`source: "ephemeral"`, `warning: true`). Backups bundle the active
persistent key automatically (under `secrets/.encryption_key` in the
ZIP) so a restored archive keeps the secrets readable.

## 3. Verify your setup

Boot logs should print:

```
[startup] deployment mode=B (reverse proxy) | TRUSTED_PROXIES=192.0.2.10 | FRONTEND_ORIGIN=https://mediakeeper.your-domain.example | COOKIE_SECURE=true
```

From any browser on the LAN:

```bash
curl -I https://mediakeeper.your-domain.example/api/health
# → HTTP/2 200, with security headers + HSTS

curl -i \
  -X POST https://mediakeeper.your-domain.example/api/csp-violation-report \
  -H 'Content-Type: application/csp-report' \
  -d '{"csp-report":{"violated-directive":"img-src"}}'
# → 204
```

The chat WebSocket is reachable at
`wss://mediakeeper.your-domain.example/api/portal/chat/ws/<room_id>`.
A handshake that downgrades to HTTP indicates the WebSocket toggle in
DSM is off.

## 4. Common pitfalls

- **WebSocket toggle disabled** → chat fails to connect, MediaKeeper
  logs the operator hint.
- **Custom Header tab empty** → MediaKeeper sees DSM's loopback IP as
  the client, cookies do not gain the `Secure` flag, the CSRF Origin
  check rejects requests because `Host` is the LAN name instead of
  the public hostname.
- **Multiple reverse-proxy hops** (DSM → CDN) → list every
  intermediate IP / CIDR in `TRUSTED_PROXIES` (CSV).
