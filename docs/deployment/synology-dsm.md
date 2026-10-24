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
| Destination — Hostname | `127.0.0.1` |
| Destination — Port | 8888 |

DSM 7 already forwards `Host`, `X-Forwarded-For` and
`X-Forwarded-Proto` to the container: no custom header row is needed
for them.

In the **WebSocket** tab, tick **Enable WebSocket**. Without this DSM
strips the Upgrade header and the chat handshake degrades into a 426
response (visible in MediaKeeper logs as
`received an HTTP GET on the chat WebSocket path`).

DSM 7.2+ also honours HTTP/2 in this same tab — leave it on for
better Vue bundle delivery.

## 2. MediaKeeper environment

Drop these lines in `/etc/mediakeeper.env`:

```dotenv
# DSM's reverse proxy reaches the container through the Docker network
# gateway, not through the NAS's LAN IP. Read it with
# `docker network inspect <project>_default` (Gateway field).
TRUSTED_PROXIES=172.18.0.1
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

`TRUSTED_PROXIES` is what unlocks `X-Forwarded-*` honouring;
`FRONTEND_ORIGIN` switches the chat WS guard from auto-derive to a
strict allowlist; `COOKIE_SECURE=true` is redundant once HTTPS is
detected, but explicit is better when DSM ever swaps to a non-stable
intermediate hop.

Publish the port on the loopback only (`127.0.0.1:8888:8888` in the
compose file). DSM reaches it through `127.0.0.1`, and Docker on DSM
relays every connection to a published port from that same gateway:
with the port open to the LAN, any device could choose its address.

The gateway can change if the Compose network is recreated. Docker's
usual private range is a wider alternative:

```dotenv
TRUSTED_PROXIES=172.16.0.0/12
```

It also trusts every container on MediaKeeper's network, which could
then choose the address MediaKeeper records. Do not use a LAN range
such as `192.168.0.0/16`: DSM does not connect from it, and any LAN
device could choose that address.

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
[startup] deployment mode=B (reverse proxy) | TRUSTED_PROXIES=172.18.0.1 | FRONTEND_ORIGIN=https://mediakeeper.your-domain.example | COOKIE_HTTPS_FLAG=true
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
- **Every visitor shows the same address** in the Security tab of the
  settings → `TRUSTED_PROXIES` does not match the address DSM connects
  from. Three wrong passwords would then block everyone.
- **A CDN in front of DSM** → list the CDN's ranges in
  `TRUSTED_PROXIES`. DSM already appends to the CDN's
  `X-Forwarded-For`.
