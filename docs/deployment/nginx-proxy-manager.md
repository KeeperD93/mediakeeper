# Deployment — Nginx Proxy Manager (Mode B)

Nginx Proxy Manager (NPM) is the most common reverse-proxy stack for
self-hosters running on Docker. This guide spans a fresh proxy host
that terminates TLS via Let's Encrypt and forwards to the MediaKeeper
container.

## 1. Proxy host

Create a new **Proxy Host** with the following:

| Tab | Field | Value |
|---|---|---|
| Details | Domain Names | `mediakeeper.your-domain.example` |
| Details | Scheme | `http` |
| Details | Forward Hostname / IP | `mediakeeper` (Docker service name) or `192.0.2.10` |
| Details | Forward Port | `8888` |
| Details | Cache Assets | off (Vue bundle is hash-named already) |
| Details | Block Common Exploits | on |
| Details | Websockets Support | **on** |
| SSL | SSL Certificate | request a new Let's Encrypt cert |
| SSL | Force SSL | on |
| SSL | HTTP/2 Support | on |
| SSL | HSTS Enabled | leave off — MediaKeeper emits HSTS itself once the request is HTTPS |

The Websockets toggle is what enables NPM to forward the
`Upgrade: websocket` header. Without it, the chat WebSocket falls
back to HTTP and MediaKeeper logs `received an HTTP GET on the chat
WebSocket path`.

## 2. Custom locations / advanced (optional)

If you ever need to add headers manually, the **Advanced** tab accepts
raw nginx directives. The default location block already forwards the
forwarded headers — you only need to add a custom block when running
behind another proxy upstream of NPM (Cloudflare, Tailscale Funnel…).

## 3. MediaKeeper environment

```dotenv
# 172.17.0.1 is the default Docker bridge gateway as seen from inside
# the MediaKeeper container; substitute the actual NPM container IP
# (or its CIDR) on your network.
TRUSTED_PROXIES=172.17.0.0/16
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

`TRUSTED_PROXIES` accepts a CIDR so you don't have to update it every
time NPM's container restarts on a different IP. Limit the CIDR as
narrowly as your network design allows.

## 4. Verify your setup

```bash
curl -I https://mediakeeper.your-domain.example/api/health
# → HTTP/2 200 with HSTS + security headers
```

From a browser DevTools console, on the public origin:

```js
const ws = new WebSocket("wss://mediakeeper.your-domain.example/api/portal/chat/ws/1");
ws.onopen = () => console.log("upgraded ✔");
ws.onerror = e => console.error("upgrade failed", e);
```

A failed handshake means the Websockets toggle in NPM is off.

## 5. Common pitfalls

- **HSTS toggled on in NPM** → both NPM and MediaKeeper emit the
  header; pick one (MediaKeeper is recommended because the value
  matches the rest of the security headers).
- **Block Common Exploits on with a custom CSP** → harmless but
  duplicates MediaKeeper's CSP.
- **Multiple domains** pointing at the same proxy host → list every
  one in `FRONTEND_ORIGIN` (CSV) so chat WS handshakes from the
  alternate hostname pass the allowlist.
