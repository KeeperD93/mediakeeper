# Deployment — Traefik (Mode B)

Traefik discovers MediaKeeper via Docker labels — no separate config
file once the routing is captured on the container itself.

## 1. docker-compose.yml

```yaml
services:
  mediakeeper:
    image: ghcr.io/keeperd93/mediakeeper:beta
    env_file: /etc/mediakeeper.env
    networks: [public]
    volumes:
      - /srv/mediakeeper/data:/data
      - /srv/mediakeeper/media:/media
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mediakeeper.rule=Host(`mediakeeper.your-domain.example`)"
      - "traefik.http.routers.mediakeeper.entrypoints=websecure"
      - "traefik.http.routers.mediakeeper.tls.certresolver=letsencrypt"
      - "traefik.http.services.mediakeeper.loadbalancer.server.port=8888"
      # WebSocket support is automatic in Traefik — no explicit middleware
      # needed. The router handles HTTP/1.1 Upgrade transparently.

networks:
  public:
    external: true
```

Restart the stack: `docker compose up -d --force-recreate mediakeeper`.

## 2. MediaKeeper environment

```dotenv
# Traefik's IP on the `public` network. Print Traefik's IPs, one line
# per network, with
#   docker inspect <traefik-container> --format '{{range $net, $cfg := .NetworkSettings.Networks}}{{$net}} {{$cfg.IPAddress}}{{println}}{{end}}'
TRUSTED_PROXIES=172.18.0.2
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

List Traefik's own address, not the `public` network: every container
on it would be trusted too. Pin it with `ipv4_address` (on a network
created with a fixed subnet) so it survives a restart. Visitors that
Docker relays show up as the network gateway: IPv6 ones unless the
network has IPv6 enabled, and all of them on Synology. There, use
DSM's reverse proxy ([synology-dsm.md](synology-dsm.md)).

## 3. Verify your setup

```bash
curl -i https://mediakeeper.your-domain.example/api/health
# → HTTP/2 200, HSTS + Content-Security-Policy
```

Boot logs from MediaKeeper should mention Mode B with the matching
`TRUSTED_PROXIES` / `FRONTEND_ORIGIN`.

```text
[startup] deployment mode=B (reverse proxy) | TRUSTED_PROXIES=172.18.0.2 | FRONTEND_ORIGIN=https://mediakeeper.your-domain.example | COOKIE_HTTPS_FLAG=true
```

## 4. Common pitfalls

- **Wrong `loadbalancer.server.port`** → 502 from Traefik even though
  the container is healthy.
- **Missing entrypoint** → `traefik.http.routers.mediakeeper.entrypoints`
  must match what your static config exposes (`websecure` is the
  usual name for HTTPS).
- **Multiple Docker networks** → MediaKeeper must be on the same
  network as Traefik; the `networks: [public]` line in the compose
  attaches it.
- **Traefik behind a CDN** → list the CDN's ranges both in Traefik's
  `entryPoints.<name>.forwardedHeaders.trustedIPs` (otherwise Traefik
  drops the CDN's `X-Forwarded-For`) and in `TRUSTED_PROXIES`.
- **Every visitor shows the same address** in the Security tab of the
  settings → `TRUSTED_PROXIES` does not match Traefik's address, or
  Docker relays your visitors to Traefik (section 2). Three wrong
  passwords would then block everyone.
- **WebSocket failing** → turn on Traefik's access log: a `101` status
  on `/api/portal/chat/ws/` means Traefik forwarded the upgrade, and the
  issue is downstream (CSRF / Origin guard, see [direct-lan.md](direct-lan.md)
  for the verification curl commands).
