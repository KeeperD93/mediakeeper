# Deployment guides

Pick the guide that matches your reverse-proxy stack. Every guide
keeps to a single page, ends with a "Verify your setup" section, and
relies on the same three environment variables on the MediaKeeper
side: `TRUSTED_PROXIES`, `FRONTEND_ORIGIN`, `COOKIE_SECURE`.

| Stack | Guide | When to pick |
|---|---|---|
| Direct LAN, no proxy | [direct-lan.md](direct-lan.md) | Trial, home lab, VPN-only access |
| Synology DSM | [synology-dsm.md](synology-dsm.md) | NAS-hosted instance, DSM ≥ 7.x |
| Nginx Proxy Manager | [nginx-proxy-manager.md](nginx-proxy-manager.md) | Self-hosters with NPM already in place |
| Caddy | [caddy.md](caddy.md) | Smallest moving parts, automatic Let's Encrypt |
| Traefik | [traefik.md](traefik.md) | Docker Compose stacks driven by labels |

If your stack is not listed, the contract is identical to the others:

1. Forward `X-Forwarded-Proto`, `X-Forwarded-For`, `X-Forwarded-Host`
   to MediaKeeper on port `8888`.
2. Forward the WebSocket `Upgrade` and `Connection` headers (chat
   WebSocket lives at `/api/portal/chat/ws/<room_id>`).
3. List the proxy IP or CIDR in `TRUSTED_PROXIES` so MediaKeeper
   honours the forwarded headers.
4. Set `FRONTEND_ORIGIN` to the public origin so the chat WebSocket
   guard switches to strict-allowlist mode.

The TLS deployment guide at [../operations/tls-deployment.md](../operations/tls-deployment.md)
covers cross-cutting concerns (HSTS, certificate rotation, CSP report
endpoint) that apply across every stack.
