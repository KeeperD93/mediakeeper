"""Unit + integration tests for :mod:`core.log_redaction`."""
import logging
from types import SimpleNamespace

import pytest

from core.log_redaction import (
    LogRedactor,
    REDACTED,
    install_log_redactor,
    safe_request_url,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(message: str, *args) -> logging.LogRecord:
    return logging.LogRecord(
        name="mediakeeper.tests",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=message,
        args=args or None,
        exc_info=None,
    )


def _redacted(message: str, *args) -> str:
    record = _make_record(message, *args)
    LogRedactor().filter(record)
    return record.getMessage()


# ---------------------------------------------------------------------------
# Patterns — positive matches
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected_substring",
    [
        ("password=hunter2", "password=" + REDACTED),
        ("password = hunter2", "password=" + REDACTED),
        ("password:hunter2", "password=" + REDACTED),
        ("Password=Hunter2", "Password=" + REDACTED),
        ('"password":"hunter2"', "password=" + REDACTED),
        ("pwd=secret", "pwd=" + REDACTED),
        ("passwd=secret", "passwd=" + REDACTED),
    ],
)
def test_redacts_password_variants(raw, expected_substring):
    assert expected_substring in _redacted(raw)
    assert "hunter2" not in _redacted(raw).lower()
    assert "secret" not in _redacted(raw).lower()


@pytest.mark.parametrize(
    "raw,expected_key",
    [
        ("token=abc123def456", "token"),
        ("api_key=AIzaSyEXAMPLE", "api_key"),
        ("apikey=AIzaSyEXAMPLE", "apikey"),
        ("api-key=AIzaSyEXAMPLE", "api-key"),
        ("access_token=at-secret-value", "access_token"),
    ],
)
def test_redacts_token_keys(raw, expected_key):
    out = _redacted(raw)
    assert f"{expected_key}={REDACTED}" in out


@pytest.mark.parametrize(
    "raw,key,secret",
    [
        ("client_secret=oauth-app-secret", "client_secret", "oauth-app-secret"),
        ("refresh_token=rt-very-secret", "refresh_token", "rt-very-secret"),
        ("auth_token=auth-distinct", "auth_token", "auth-distinct"),
        ("bearer_token=bt-distinct", "bearer_token", "bt-distinct"),
        ("id_token=id-distinct-val", "id_token", "id-distinct-val"),
        ("session_token=st-distinct", "session_token", "st-distinct"),
        ("session_key=sesskey-distinct", "session_key", "sesskey-distinct"),
        ("private_key=pem-blob-distinct", "private_key", "pem-blob-distinct"),
        ("pkey=pk-distinct", "pkey", "pk-distinct"),
        ("webhook_url=https://hooks.example/secretpath", "webhook_url", "secretpath"),
        ("secret=plain-distinct", "secret", "plain-distinct"),
        ("jwt=opaque-distinct", "jwt", "opaque-distinct"),
    ],
)
def test_redacts_oauth_and_secret_keys(raw, key, secret):
    """Defence-in-depth keywords added to the redaction pattern: the value
    must be removed and the key kept. Compound (underscored) forms are listed
    explicitly because the bare 'token'/'secret' alternatives cannot match
    inside a compound key (no word boundary after '_')."""
    out = _redacted(raw)
    assert f"{key}={REDACTED}" in out
    assert secret not in out


def test_redacts_bearer_jwt():
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.signaturepart"
    out = _redacted(raw)
    assert f"Bearer {REDACTED}" in out
    assert "eyJhbGciOiJIUzI1NiJ9" not in out


def test_redacts_standalone_jwt():
    raw = "trace: token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.sigsigsig embedded"
    out = _redacted(raw)
    assert "eyJhbGci" not in out
    assert REDACTED in out


def test_redacts_discord_webhook_token_keeps_id():
    raw = "POST https://discord.com/api/webhooks/123456789012345678/abcDEF-secret_TOKEN-x"
    out = _redacted(raw)
    assert "https://discord.com/api/webhooks/123456789012345678/" in out
    assert REDACTED in out
    assert "abcDEF-secret_TOKEN-x" not in out


@pytest.mark.parametrize(
    "raw,key",
    [
        ("Cookie: mk_token=long-cookie-value-here", "mk_token"),
        ("Cookie: mk_csrf=csrf-cookie-value", "mk_csrf"),
        ("Cookie: rq_token=portal-cookie-value", "rq_token"),
    ],
)
def test_redacts_mediakeeper_cookies(raw, key):
    out = _redacted(raw)
    assert f"{key}={REDACTED}" in out


def test_redacts_password_in_url_query():
    raw = "GET /login?password=hunter2&next=/home"
    out = _redacted(raw)
    assert f"password={REDACTED}" in out
    assert "hunter2" not in out


def test_redacts_inside_lazy_format_args():
    """logger.info('password=%s', 'x') must redact at filter time."""
    record = _make_record("password=%s", "hunter2")
    LogRedactor().filter(record)
    assert "hunter2" not in record.getMessage()
    assert REDACTED in record.getMessage()


# ---------------------------------------------------------------------------
# Patterns — negative cases (false-positive guards)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw",
    [
        "the token of peace was negotiated",
        "user requested a password reset email",
        "Bearer with a sword charged the gate",
        "the api key file is missing",  # no = / : separator
        "token de paix",  # French sentence, same shape
    ],
)
def test_does_not_redact_conversational_phrases(raw):
    assert _redacted(raw) == raw


def test_subkey_not_matched():
    # "subtoken" must not be matched as "token" because of the leading
    # word-boundary in the pattern.
    raw = "logged subtoken counter=42"
    assert _redacted(raw) == raw


def test_short_bearer_value_not_redacted():
    # Short post-Bearer text that is plausibly conversational stays as-is.
    raw = "Bearer hi"
    assert _redacted(raw) == raw


# ---------------------------------------------------------------------------
# install_log_redactor — handler-level wiring
# ---------------------------------------------------------------------------

def test_install_log_redactor_attaches_to_existing_handlers():
    root = logging.getLogger()
    handler = logging.NullHandler()
    root.addHandler(handler)
    try:
        install_log_redactor()
        assert any(isinstance(f, LogRedactor) for f in handler.filters)
    finally:
        root.removeHandler(handler)


def test_install_log_redactor_is_idempotent():
    root = logging.getLogger()
    handler = logging.NullHandler()
    root.addHandler(handler)
    try:
        install_log_redactor()
        install_log_redactor()
        redactors = [f for f in handler.filters if isinstance(f, LogRedactor)]
        assert len(redactors) == 1
    finally:
        root.removeHandler(handler)


def test_handler_attached_filter_redacts_propagated_records(caplog):
    """A child logger emitting a sensitive value reaches the handler-attached
    filter via propagation, and the handler sees a redacted message."""
    redactor = LogRedactor()
    caplog.handler.addFilter(redactor)
    try:
        with caplog.at_level(logging.INFO):
            logging.getLogger("mediakeeper.tests.child").info("password=hunter2")
        rendered = "\n".join(r.getMessage() for r in caplog.records)
        assert "hunter2" not in rendered
        assert REDACTED in rendered
    finally:
        caplog.handler.removeFilter(redactor)


def test_filter_does_not_swallow_records_with_format_errors():
    """A bad format string must not stop the record from emitting."""
    record = _make_record("bad format %s %s", "only-one")
    # Should not raise — filter must return True.
    assert LogRedactor().filter(record) is True


# ---------------------------------------------------------------------------
# safe_request_url
# ---------------------------------------------------------------------------

def _fake_request(url_obj):
    return SimpleNamespace(url=url_obj)


def test_safe_request_url_strips_query_string():
    url = SimpleNamespace(
        scheme="https", netloc="mediakeeper.example", path="/login",
        query="next=/home&token=secret",
    )
    assert (
        safe_request_url(_fake_request(url))
        == "https://mediakeeper.example/login"
    )


def test_safe_request_url_handles_request_without_url():
    assert safe_request_url(SimpleNamespace()) == ""


def test_safe_request_url_falls_back_to_path_when_scheme_missing():
    url = SimpleNamespace(scheme="", netloc="", path="/api/health")
    assert safe_request_url(_fake_request(url)) == "/api/health"


def test_safe_request_url_drops_fragment_too():
    url = SimpleNamespace(
        scheme="http", netloc="localhost:8000", path="/api/x",
        query="", fragment="secret",
    )
    assert safe_request_url(_fake_request(url)) == "http://localhost:8000/api/x"
