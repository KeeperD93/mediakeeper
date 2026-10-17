"""The rule for a stored poster or backdrop URL, shared by requests, featured
titles and lists."""
from __future__ import annotations

from core.url_safety import ALLOWED_IMAGE_HOST, safe_url
from services.portal.image_cache import unproxied_url

# Hosts a stored poster or backdrop may point to: the CSP ``img-src``
# whitelist (core/security_headers.py), so the portal can always show it.
STORED_IMAGE_HOSTS = (ALLOWED_IMAGE_HOST, "i.imgur.com")


def safe_image_url(raw: str | None) -> str | None:
    """The poster or backdrop URL to store, or None when it is unsafe: the
    cache-proxy wrapper is undone first, then only https on those hosts."""
    return safe_url(unproxied_url(raw or ""), allowed_hosts=STORED_IMAGE_HOSTS)
