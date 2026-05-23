# Deployment — Direct LAN (Mode A)

The simplest deployment path: expose MediaKeeper directly on the local
network, no reverse proxy in front. Recommended for trial setups, home
labs, or teams that already terminate TLS at the firewall.

This guide assumes you have already pulled the container image and
mounted persistent volumes per the README.

## 1. Container

Run the published image:

```bash
docker run -d \
  --name mediakeeper \
  -p 8888:8888 \
  -v /srv/mediakeeper/data:/data \
  -v /srv/mediakeeper/media:/media \
  --env-file /etc/mediakeeper.env \
  ghcr.io/keeperd93/mediakeeper:latest
```

`/etc/mediakeeper.env` carries the secrets (`JWT_SECRET_KEY` is
mandatory, the rest is optional).

## 2. Environment

Mode A keeps the trust signals empty:

```dotenv
# Direct LAN — no reverse proxy in front
TRUSTED_PROXIES=
FRONTEND_ORIGIN=
COOKIE_SECURE=false
```

Empty `FRONTEND_ORIGIN` opts the chat WebSocket into the auto-derive
guard (Origin compared against the `Host` header). MediaKeeper writes
one WARN line at boot reminding you to lock this down once you settle
on a permanent hostname.

If you reach the UI over HTTPS via a self-signed certificate or VPN,
flip `COOKIE_SECURE=true` so session cookies stop downgrading.

### Persistent encryption key

Even on a direct-LAN deployment, set `MEDIAKEEPER_ENCRYPTION_KEY`
**before the first `docker compose up`** so encrypted secrets
(integration tokens, Discord URLs…) survive a container restart:

```dotenv
MEDIAKEEPER_ENCRYPTION_KEY=<paste your fernet key here>
```

Without it, MediaKeeper boots on an in-memory key and the admin UI
shows a persistent red banner; values written under that key become
unreadable as soon as the container restarts.

## 3. Verify your setup

After boot, the container logs should show:

```
[startup] deployment mode=A (direct LAN) | TRUSTED_PROXIES=(empty) | FRONTEND_ORIGIN=auto-derived | COOKIE_HTTPS_FLAG=auto
```

Then from a client on the same LAN:

```bash
# Health endpoint — must return 200 with security headers.
curl -I http://192.0.2.10:8888/api/health

# Login — must return 200 with Set-Cookie.
curl -i -X POST http://192.0.2.10:8888/api/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"username":"admin","password":"<your-password>"}'
```

The chat WebSocket is reachable at `ws://192.0.2.10:8888/api/portal/chat/ws/<room_id>`.

## 4. When to switch to Mode B

Move to a reverse proxy when any of these become true:

- The service is reachable from the public Internet.
- You want browser-trusted TLS without ad-hoc certificate management.
- You expose a friendly hostname (`mediakeeper.lan`) instead of an IP.

The matching guides — [synology-dsm.md](synology-dsm.md),
[nginx-proxy-manager.md](nginx-proxy-manager.md),
[caddy.md](caddy.md), [traefik.md](traefik.md) — share the same Mode B
contract: set `TRUSTED_PROXIES` to the proxy IP or CIDR, set
`FRONTEND_ORIGIN` to the public origin, and forward the WebSocket
upgrade headers.
