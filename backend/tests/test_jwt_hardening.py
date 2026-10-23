"""Pins the JWT decode contract against the attack vectors that
PYSEC-2025-183 / CVE-2025-45768 informally cover.

The advisory itself is disputed by the PyJWT maintainers (the
weakness it describes is "the application picked a short key" — not a
library bug). MediaKeeper enforces a >= 32-byte JWT_SECRET_KEY at
startup (core/security.py), but the runtime guard alone does not stop
forgery attempts: ``decode_access_token`` must also refuse tokens
signed with the wrong key, the wrong algorithm, "alg: none", a
tampered signature, or past their ``exp``. It must also fail closed
(``None``) on malformed input instead of raising, refuse a token missing
one of the claims MediaKeeper always sets, and refuse an oversized one
before parsing it.

If any of these tests start failing, the project IS exposed,
regardless of what the advisory database says."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from core.security import (
    ALGORITHM,
    MAX_TOKEN_LENGTH,
    SECRET_KEY,
    create_access_token,
    decode_access_token,
)


def _payload_with_exp(minutes: int = 10) -> dict:
    return {
        "sub": "alice",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
    }


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def test_decode_accepts_valid_token():
    """Sanity check: a token signed with the real key and algorithm decodes."""
    token = create_access_token({"sub": "alice"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "alice"


def test_decode_rejects_alg_none_token():
    """``alg: none`` strips the signature entirely; PyJWT must refuse it
    because ``algorithms=[ALGORITHM]`` excludes "none"."""
    forged = jwt.encode(_payload_with_exp(), key="", algorithm="none")
    assert decode_access_token(forged) is None


def test_decode_rejects_token_signed_with_other_key():
    """A token signed with the right algorithm but the wrong key must fail
    signature verification."""
    forged = jwt.encode(
        _payload_with_exp(),
        key="x" * len(SECRET_KEY),
        algorithm=ALGORITHM,
    )
    assert decode_access_token(forged) is None


def test_decode_rejects_token_signed_with_other_hmac_algorithm():
    """A token signed with HS512 (or any HMAC variant other than HS256) must
    be rejected — the decode call pins ``algorithms=["HS256"]``."""
    forged = jwt.encode(_payload_with_exp(), key=SECRET_KEY, algorithm="HS512")
    assert decode_access_token(forged) is None


def test_decode_rejects_tampered_signature():
    """Flipping a single byte of the signature segment must invalidate the
    token."""
    valid = create_access_token({"sub": "alice"})
    header, payload, signature = valid.split(".")
    # Flip a middle character: the last one also carries 2 padding bits, so a
    # swap there can leave the decoded bytes unchanged and only trip the
    # decoder's canonical-encoding check instead of signature verification.
    middle = len(signature) // 2
    pivot = signature[middle]
    swapped = "B" if pivot != "B" else "C"
    tampered_sig = f"{signature[:middle]}{swapped}{signature[middle + 1:]}"
    tampered = f"{header}.{payload}.{tampered_sig}"
    assert decode_access_token(tampered) is None


def test_decode_rejects_expired_token():
    """An expired ``exp`` claim must trigger an
    ``ExpiredSignatureError`` that the helper swallows into ``None``."""
    token = create_access_token(
        {"sub": "alice"},
        expires_delta=timedelta(seconds=-1),
    )
    assert decode_access_token(token) is None


def test_decode_rejects_deeply_nested_header():
    """A header nested past the JSON parser's recursion limit must be refused
    like any malformed token: PyJWT < 2.14 let the ``RecursionError`` escape,
    so an unauthenticated cookie could turn any protected route into a 500.
    Such a header is now far over the length cap, refused before parsing."""
    depth = 200_000  # well past CPython's limit on every supported platform
    header = _b64url(b"[" * depth + b"]" * depth)
    forged = f"{header}.{_b64url(b'{}')}.{_b64url(b'sig')}"
    assert decode_access_token(forged) is None


@pytest.mark.parametrize("missing", ["exp", "iat", "sub"])
def test_decode_requires_exp_iat_and_sub(missing):
    """Every token MediaKeeper mints carries the three claims: a signed token
    lacking one is refused (a token without ``exp`` would never expire)."""
    claims = {k: v for k, v in _payload_with_exp().items() if k != missing}
    token = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)
    assert decode_access_token(token) is None


def test_decode_refuses_oversized_token_before_parsing(monkeypatch):
    """A value over the cap is forged: PyJWT must not even see it."""
    calls = []
    monkeypatch.setattr(jwt, "decode", lambda *a, **k: calls.append(1))
    assert decode_access_token("A" * (MAX_TOKEN_LENGTH + 1)) is None
    assert calls == []


def test_decode_refuses_genuine_but_oversized_token():
    padded = create_access_token({"sub": "alice", "pad": "x" * MAX_TOKEN_LENGTH})
    assert decode_access_token(padded) is None


def test_longest_realistic_token_fits_under_the_cap():
    """``User.username`` holds 50 characters; emoji are the worst case
    (JSON-escaped to 12 bytes each before base64)."""
    username = "\U0001f600" * 50
    token = create_access_token({"sub": username, "scope": "portal"})
    assert len(token) < MAX_TOKEN_LENGTH
    assert decode_access_token(token)["sub"] == username


@pytest.mark.asyncio
async def test_oversized_cookie_gets_401_without_parsing(client, monkeypatch):
    calls = []
    real_decode = jwt.decode
    monkeypatch.setattr(jwt, "decode", lambda *a, **k: calls.append(1) or real_decode(*a, **k))
    client.cookies.set("mk_token", "A" * 300_000)
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "token_invalid"
    assert calls == []
