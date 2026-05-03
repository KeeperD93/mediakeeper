# Deployment — Traefik (Mode B)

Traefik discovers MediaKeeper via Docker labels — no separate config
file once the routing is captured on the container itself.

## 1. docker-compose.yml

```yaml
services:
  mediakeeper:
    image: ghcr.io/<your-org>/mediakeeper:latest
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
# Traefik's container IP / CIDR as seen from MediaKeeper. The default
# Docker network gateway is usually 172.17.0.0/16; check yours with:
#   docker inspect mediakeeper --format='{{ .NetworkSettings.Networks }}'
TRUSTED_PROXIES=172.17.0.0/16
FRONTEND_ORIGIN=https://mediakeeper.your-domain.example
COOKIE_SECURE=true
```

## 3. Verify your setup

```bash
curl -I https://mediakeeper.your-domain.example/api/health
# → HTTP/2 200, HSTS + Content-Security-Policy
```

Boot logs from MediaKeeper should mention Mode B with the matching
`TRUSTED_PROXIES` / `FRONTEND_ORIGIN`.

```text
[startup] deployment mode=B (reverse proxy) | TRUSTED_PROXIES=172.17.0.0/16 | FRONTEND_ORIGIN=https://mediakeeper.your-domain.example | COOKIE_SECURE=true
```

## 4. Common pitfalls

- **Wrong `loadbalancer.server.port`** → 502 from Traefik even though
  the container is healthy.
- **Missing entrypoint** → `traefik.http.routers.mediakeeper.entrypoints`
  must match what your static config exposes (`websecure` is the
  Traefik default for HTTPS).
- **Multiple Docker networks** → MediaKeeper must be on the same
  network as Traefik; the `networks: [public]` line in the compose
  attaches it.
- **WebSocket failing** → check the LAN-side `docker logs traefik`
  output; if you see HTTP/1.1 101 with the right headers, the issue
  is downstream (CSRF / Origin guard, see [direct-lan.md](direct-lan.md)
  for the verification curl commands).
