# Deployment guides

Pick the guide that matches your reverse-proxy stack. Every guide
keeps to a single page, has a "Verify your setup" section, and
relies on the same three environment variables on the MediaKeeper
side: `TRUSTED_PROXIES`, `FRONTEND_ORIGIN`, `COOKIE_SECURE`. Set them in
the `environment:` section of MediaKeeper's compose file, or in an env
file it loads with `env_file:`.

| Stack | Guide | When to pick |
|---|---|---|
| Direct LAN, no proxy | [direct-lan.md](direct-lan.md) | Trial, home lab, VPN-only access |
| Synology DSM | [synology-dsm.md](synology-dsm.md) | NAS-hosted instance, DSM ≥ 7.x |
| Nginx Proxy Manager | [nginx-proxy-manager.md](nginx-proxy-manager.md) | Self-hosters with NPM already in place |
| Caddy | [caddy.md](caddy.md) | Smallest moving parts, automatic Let's Encrypt |
| Traefik | [traefik.md](traefik.md) | Docker Compose stacks driven by labels |

If your stack is not listed, the contract is identical to the others:

1. Forward `X-Forwarded-Proto`, `X-Forwarded-For` and the public
   `Host` (or `X-Forwarded-Host`) to MediaKeeper on port `8888`.
2. Forward the WebSocket `Upgrade` and `Connection` headers (chat
   WebSocket lives at `/api/portal/chat/ws/<room_id>`).
3. List every proxy between the visitor and MediaKeeper in
   `TRUSTED_PROXIES`, a CDN or a tunnel included. List the address
   each one connects from, never a whole LAN range: any device on it
   could then choose the address MediaKeeper records. MediaKeeper reads
   `X-Forwarded-For` from the right and keeps the first address that is
   not a listed proxy, so a proxy behind another one must append to it.
   A proxy on the Docker host connects from the Docker network gateway
   (`docker network inspect <project>_default`), not from `127.0.0.1`.
   Docker can relay other connections to a published port from that
   gateway too (IPv6 visitors, and every visitor on Synology), so
   publish MediaKeeper on the loopback only (`127.0.0.1:8888:8888`).
   After a wrong password, the Security tab of the settings should
   show your own address, not the proxy's.
4. Set `FRONTEND_ORIGIN` to the public origin so the chat WebSocket
   guard switches to strict-allowlist mode. Leaving it empty in Mode B
   triggers a one-shot startup WARN reminding you to set it (CORS
   preflights need it even though CSRF auto-derives).

The TLS deployment guide at [../operations/tls-deployment.md](../operations/tls-deployment.md)
covers cross-cutting concerns (HSTS, Secure cookies, CSP mode) that
apply across every stack.
