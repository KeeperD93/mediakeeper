"""Pins the JWT decode contract against the attack vectors that
PYSEC-2025-183 / CVE-2025-45768 informally cover.

The advisory itself is disputed by the PyJWT maintainers (the
weakness it describes is "the application picked a short key" — not a
library bug). MediaKeeper enforces a >= 32-byte JWT_SECRET_KEY at
startup (core/security.py), but the runtime guard alone does not stop
forgery attempts: ``decode_access_token`` must also refuse tokens
signed with the wrong key, the wrong algorithm, "alg: none", a
tampered signature, or past their ``exp``.

If any of these tests start failing, the project IS exposed,
regardless of what the advisory database says."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from core.security import (
    ALGORITHM,
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
    last = signature[-1]
    swapped = "B" if last != "B" else "C"
    tampered = f"{header}.{payload}.{signature[:-1]}{swapped}"
    assert decode_access_token(tampered) is None


def test_decode_rejects_expired_token():
    """An expired ``exp`` claim must trigger an
    ``ExpiredSignatureError`` that the helper swallows into ``None``."""
    token = create_access_token(
        {"sub": "alice"},
        expires_delta=timedelta(seconds=-1),
    )
    assert decode_access_token(token) is None
