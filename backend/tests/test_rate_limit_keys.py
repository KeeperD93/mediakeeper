"""Rate-limit keys: per-account budgets read the right session cookie and fall
back to the client IP when it is missing or unusable. Synthetic users only."""
from __future__ import annotations

from starlette.requests import Request

from core.rate_limit import admin_user_or_ip_key, ip_key, portal_user_or_ip_key
from core.security import MAX_TOKEN_LENGTH, create_access_token

CLIENT_IP = "203.0.113.5"


def _request(**cookies: str) -> Request:
    cookie_header = "; ".join(f"{name}={value}" for name, value in cookies.items())
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"cookie", cookie_header.encode())] if cookies else [],
        "client": (CLIENT_IP, 1234),
    })


def test_admin_key_follows_the_admin_cookie():
    token = create_access_token({"sub": "alice", "scope": "admin"})
    assert admin_user_or_ip_key(_request(mk_token=token)) == "user:alice"


def test_admin_key_ignores_the_portal_cookie():
    token = create_access_token({"sub": "alice", "scope": "portal"})
    assert admin_user_or_ip_key(_request(rq_token=token)) == f"ip:{CLIENT_IP}"


def test_portal_key_follows_the_portal_cookie():
    token = create_access_token({"sub": "bob", "scope": "portal"})
    assert portal_user_or_ip_key(_request(rq_token=token)) == "user:bob"


def test_keys_fall_back_to_the_ip_for_an_unusable_cookie():
    # Validly signed but past the size cap: only the cap makes it unusable.
    oversized = create_access_token({"sub": "alice", "scope": "admin", "pad": "x" * MAX_TOKEN_LENGTH})
    assert admin_user_or_ip_key(_request(mk_token=oversized)) == f"ip:{CLIENT_IP}"
    assert portal_user_or_ip_key(_request(rq_token="not-a-jwt")) == f"ip:{CLIENT_IP}"


def test_ip_key_is_the_normalized_client_ip_or_one_fixed_bucket():
    def key(client):
        return ip_key(Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": client}))

    assert key(("::ffff:203.0.113.5", 1234)) == CLIENT_IP
    # Without a usable client IP every request shares one bucket the client cannot vary.
    assert key(None) == "unknown"
    assert key(("x" * 200, 1234)) == "unknown"
