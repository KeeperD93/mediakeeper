# TLS deployment — operator guide

MediaKeeper ships as a single container that listens on plain HTTP at
port `8888`. Production deployments are expected to terminate TLS in
front of the container with a reverse proxy. This guide walks through
that deployment: how to configure the proxy, how to make MediaKeeper
trust it, and how to verify the result.

The application emits security headers (CSP, HSTS, X-Frame-Options,
etc.) by itself, so a proxy that only forwards traffic without setting
its own headers is sufficient. Cookie `Secure` flags and the real
client IP are activated automatically once MediaKeeper recognises
the proxy as trusted.

---

## 1. Prerequisites

- A DNS name pointing at the host running the container. Throughout
  this guide we use `mediakeeper.example.com` as a placeholder —
  replace it with the name you actually own.
- The MediaKeeper container reachable from the proxy on port `8888`
  (loopback, Docker bridge network or any other private interface).
- A TLS certificate. Two paths are documented below:
  - automatic Let's Encrypt issuance (Caddy or Nginx with certbot);
  - a self-signed certificate for purely local LAN use.

> ⚠️ The container must **not** be exposed directly on a public
> interface. Always put it behind a TLS-terminating proxy when the
> network is reachable from outside the trusted LAN.

---

## 2. Reverse-proxy configuration

The two examples below are interchangeable — pick whichever you are
most comfortable operating. Both produce the same observable behaviour
on MediaKeeper's side.

### 2.1 Caddy (Let's Encrypt automatic)

```caddy
mediakeeper.example.com {
    encode gzip

    reverse_proxy 127.0.0.1:8888 {
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-For   {remote}
        header_up X-Forwarded-Host  {host}
    }
}
```

Caddy provisions a Let's Encrypt certificate on first start, redirects
HTTP → HTTPS and renews the certificate transparently. Run it as a
container or as a system service — both work the same way against the
backend.

### 2.2 Nginx (Let's Encrypt via certbot)

```nginx
server {
    listen 80;
    server_name mediakeeper.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mediakeeper.example.com;

    ssl_certificate     /etc/letsencrypt/live/mediakeeper.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mediakeeper.example.com/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8888;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Forwarded-For   $remote_addr;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   X-Forwarded-Host  $host;
    }
}
```

Run `certbot --nginx -d mediakeeper.example.com` to issue and renew
the certificate. The HTTP→HTTPS redirect is set up by the first
`server` block above.

### 2.3 Self-signed certificate for LAN-only use

If the instance never leaves a trusted LAN you can skip Let's Encrypt
and generate a self-signed pair:

```sh
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout mediakeeper.key -out mediakeeper.crt \
  -subj "/CN=mediakeeper.example.com"
```

Point the proxy at those files. Browsers will warn on first visit;
add the certificate to the device trust store to silence the warning.

---

## 3. MediaKeeper configuration

Two environment variables drive the proxy integration on MediaKeeper's
side. Both are read at container startup.

| Variable | Default | Purpose |
|---|---|---|
| `TRUSTED_PROXIES` | empty | CSV of CIDR/IPs allowed to set `X-Forwarded-*`. When empty the headers are ignored entirely (failsafe). |
| `COOKIE_SECURE` | unset | Force `Secure` on session cookies regardless of detection. Set to `true` once TLS is in place. |

`TRUSTED_PROXIES` accepts both bare IPs and CIDRs:

```env
TRUSTED_PROXIES=127.0.0.1
TRUSTED_PROXIES=127.0.0.1,<TRUSTED_CIDR>
```

Use the CIDR of the network the proxy lives on. Typical values:

- `127.0.0.1` — proxy and container on the same host (loopback).
- A `/16` Docker bridge network when the proxy runs as a sibling
  container, e.g. `<TRUSTED_CIDR>` such as `172.18.0.0/16`.
- `<LAN_GATEWAY>` — the gateway address of a small home LAN where
  the proxy is the only TLS-terminating box.

Set both variables in the same `.env` file used by `docker compose`:

```env
COOKIE_SECURE=true
TRUSTED_PROXIES=127.0.0.1,<TRUSTED_CIDR>
```

Restart the container (`docker compose up -d`) for the new values to
take effect.

---

## 4. What MediaKeeper does with a trusted proxy

When the direct TCP client of an incoming request matches one of the
networks in `TRUSTED_PROXIES`:

- `X-Forwarded-For` is honoured: the leftmost IP becomes the request
  client IP, used by the audit log, the rate limiter and the security
  blocklist.
- `X-Forwarded-Proto` is honoured: a value of `https` activates the
  `Secure` flag on session cookies and triggers the HSTS header.
- `X-Forwarded-Host` is honoured by the CSRF Origin/Referer check, so
  the browser-sent `Origin` is matched against the public hostname
  rather than the loopback hostname inside the container.

When the direct TCP client is **not** in the trusted set (or when the
list is empty) the headers are ignored regardless of their content.
This is the safe default for a container exposed directly on a LAN
without a proxy in front.

---

## 5. Validate the deployment

Once both sides are configured, verify the result with `curl`. Replace
the placeholder hostname with your own.

```sh
curl -I https://mediakeeper.example.com/api/health
```

Expected response headers (order may vary):

```
HTTP/2 200
content-type: application/json
content-security-policy: default-src 'self'; script-src 'self' https://www.youtube.com; ...
strict-transport-security: max-age=31536000; includeSubDomains
x-frame-options: DENY
x-content-type-options: nosniff
referrer-policy: strict-origin-when-cross-origin
permissions-policy: camera=(), microphone=(), geolocation=(), ...
```

Then verify the cookie flags by opening the login page and inspecting
the `Set-Cookie` header on `POST /api/auth/login`:

```
set-cookie: mk_token=...; HttpOnly; Secure; SameSite=lax; Path=/
set-cookie: mk_csrf=...;            Secure; SameSite=lax; Path=/
```

The presence of `Secure` proves that MediaKeeper detected the
`X-Forwarded-Proto: https` value through your trusted proxy.

---

## 6. Troubleshooting

**Cookies still emitted without `Secure` after configuring TLS.**
Check that the proxy IP belongs to one of the CIDRs declared in
`TRUSTED_PROXIES`. The container logs print one warning at startup
when no trust source is configured:
`COOKIE_SECURE is unset and TRUSTED_PROXIES is empty in
production-like mode`.
You can short-circuit detection by setting `COOKIE_SECURE=true` —
that override always wins.

**HTTP-only on a trusted LAN — silencing the warning.**
If you intentionally run MediaKeeper over plain HTTP on a LAN you
trust (no public exposure, no reverse proxy, no Internet route),
the startup warning above is informational and expected. Setting
`COOKIE_SECURE=false` in your `.env` acknowledges the trade-off
and silences the warning at every subsequent boot — the cookies
remain non-Secure, which is the only behaviour HTTP-only can
support. Do **not** use this on any host reachable from outside
the LAN: an HTTP MITM there can replay session cookies.

**Browser blocks scripts/styles/images with a Content-Security-Policy
violation.**
The shipped policy allows: `'self'` plus the YouTube IFrame API for
scripts, `'self'` plus Google Fonts for styles and `'self'` plus
TMDB/Imgur for images. If you deploy a customisation that loads other
origins, switch to `MK_CSP_MODE=report-only` for a transition window,
observe the violations in the browser console, and add the missing
origins to a custom policy before going back to enforce mode.

**HSTS header is missing.**
HSTS is emitted only when MediaKeeper sees the request as HTTPS.
That requires either `request.url.scheme == "https"` (the proxy
forwards the connection over TLS to the container, rare) or the
`X-Forwarded-Proto: https` header coming from a trusted proxy.

**`X-Forwarded-Host` ignored / CSRF rejecting same-origin requests.**
The CSRF middleware computes the canonical origin from
`X-Forwarded-Host` only when the proxy is in `TRUSTED_PROXIES`. Add
the proxy CIDR to the list, then restart the container.

**Healthcheck failing after enabling TLS.**
The Docker healthcheck is `curl -f http://localhost:8888/api/health`,
issued from inside the container against `127.0.0.1`. That request
never traverses the proxy and never sees `X-Forwarded-*`, so it is
unaffected by `TRUSTED_PROXIES`. If it fails, the issue is unrelated
to TLS — inspect `docker logs mediakeeper`.

---

## 7. See also

- [`backup-restore.md`](backup-restore.md) — operator restore runbook.
- [`runbook-incidents.md`](runbook-incidents.md) — incident response
  procedures.
- [`monitoring.md`](monitoring.md) — runtime webhook alerts.
