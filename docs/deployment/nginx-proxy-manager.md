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
| Details | Forward Hostname / IP | `mediakeeper` (Docker service name) |
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

## 2. Advanced tab

NPM appends the visitor's address to `X-Forwarded-For`, which is what
MediaKeeper expects. By default it also replaces that address with the
request's own `X-Real-IP` header when the connection comes from a
private or CDN address. LAN devices, and the visitors Docker relays to
NPM, connect from such addresses and could choose the address
MediaKeeper records. Paste this line in the proxy host's
**Advanced** tab to turn that off:

```nginx
set_real_ip_from 127.0.0.1;
```

Behind another proxy upstream of NPM (Cloudflare, Tailscale Funnel…),
also list its addresses in `TRUSTED_PROXIES`: MediaKeeper keeps the
first address, read from the right, that is not a listed proxy.

## 3. MediaKeeper environment

```dotenv
# NPM's IP on the network it shares with MediaKeeper. Print NPM's IPs,
# one line per network, with
#   docker inspect <npm-container> --format '{{range $net, $cfg := .NetworkSettings.Networks}}{{$net}} {{$cfg.IPAddress}}{{println}}{{end}}'
TRUSTED_PROXIES=172.18.0.5
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

List NPM's own address, not its network: Docker can relay visitors to
NPM from that network's gateway, and a range that includes it would
let them choose the address MediaKeeper records. Pin the address with
`ipv4_address` (on a network created with a fixed subnet) so it
survives a restart. Relayed visitors show up as that gateway: IPv6
ones unless the network has IPv6 enabled, and all of them on Synology.
There, use DSM's reverse proxy ([synology-dsm.md](synology-dsm.md)).

NPM reaches MediaKeeper by its service name once both containers share
a Docker network: an external network that both compose files join, as
in [traefik.md](traefik.md). Drop MediaKeeper's `8888:8888` port
mapping: NPM does not need it. Do not forward to the host's IP instead:
MediaKeeper would then see its own network gateway, and listing it would
let other containers on the host, and every LAN device on Synology,
choose the address MediaKeeper records.

## 4. Verify your setup

```bash
curl -i https://mediakeeper.your-domain.example/api/health
# → HTTP/2 200 with HSTS + security headers
```

From a browser DevTools console, on the public origin, signed in to the
portal (room 1 exists once someone has opened the chat):

```js
const ws = new WebSocket("wss://mediakeeper.your-domain.example/api/portal/chat/ws/1");
ws.onopen = () => console.log("upgraded ✔");
ws.onerror = e => console.error("upgrade failed", e);
```

A failed handshake then means the Websockets toggle in NPM is off.

## 5. Common pitfalls

- **HSTS toggled on in NPM** → both NPM and MediaKeeper emit the
  header; pick one (MediaKeeper is recommended because the value
  matches the rest of the security headers).
- **Block Common Exploits on with a custom CSP** → harmless but
  duplicates MediaKeeper's CSP.
- **Multiple domains** pointing at the same proxy host → list every
  one in `FRONTEND_ORIGIN` (CSV) so chat WS handshakes from the
  alternate hostname pass the allowlist.
- **Every visitor shows the same address** in the Security tab of the
  settings → `TRUSTED_PROXIES` does not match NPM's address, or Docker
  relays your visitors to NPM (section 3). Three wrong passwords would
  then block everyone. Do not add Docker's gateway to `TRUSTED_PROXIES`
  to work around it: NPM keeps the `X-Forwarded-For` a visitor sends, so
  visitors could then choose the address MediaKeeper records.
