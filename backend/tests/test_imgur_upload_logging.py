"""Tests for the structured logging emitted by the Imgur fallback path."""
import logging
from unittest.mock import AsyncMock, patch

import pytest

from services.discord._images import _upload_emby_to_imgur


class _FakeResponse:
    def __init__(self, status_code: int, *, body: str = "", content: bytes = b""):
        self.status_code = status_code
        self.text = body
        self.content = content


@pytest.fixture
def emby_image_url() -> str:
    return "http://emby.lan:8096/Items/abc/Images/Primary"


def _build_clients(*, emby_response, imgur_response):
    """Return ``(internal, external)`` httpx-like clients with mocked POST/GET."""
    internal = AsyncMock()
    internal.get = AsyncMock(return_value=emby_response)
    external = AsyncMock()
    external.post = AsyncMock(return_value=imgur_response)
    return internal, external


@pytest.mark.asyncio
async def test_imgur_401_is_logged_with_status_and_body_snippet(
    caplog, emby_image_url
):
    internal, external = _build_clients(
        emby_response=_FakeResponse(200, content=b"\x89PNG"),
        imgur_response=_FakeResponse(
            401, body='{"data":{"error":"Unauthorized"},"success":false}'
        ),
    )
    with patch(
        "services.discord._images.get_internal_client", return_value=internal
    ), patch(
        "services.discord._images.get_external_client", return_value=external
    ):
        with caplog.at_level(
            logging.WARNING, logger="mediakeeper.notifications.discord"
        ):
            url = await _upload_emby_to_imgur(emby_image_url, "emby-key", "client-id")

    assert url == ""
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert "Imgur upload failed" in rendered
    assert "status=401" in rendered
    assert "Unauthorized" in rendered
    assert "no-image embed" in rendered  # operator hint about fallback
    # Sensitive values must never reach the log.
    assert "client-id" not in rendered
    assert "emby-key" not in rendered


@pytest.mark.asyncio
async def test_imgur_500_is_logged_with_fallback_hint(caplog, emby_image_url):
    internal, external = _build_clients(
        emby_response=_FakeResponse(200, content=b"\x89PNG"),
        imgur_response=_FakeResponse(500, body="internal error"),
    )
    with patch(
        "services.discord._images.get_internal_client", return_value=internal
    ), patch(
        "services.discord._images.get_external_client", return_value=external
    ):
        with caplog.at_level(
            logging.WARNING, logger="mediakeeper.notifications.discord"
        ):
            url = await _upload_emby_to_imgur(emby_image_url, "emby-key", "client-id")

    assert url == ""
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert "status=500" in rendered
    assert "no-image embed" in rendered


@pytest.mark.asyncio
async def test_imgur_timeout_is_logged_with_exception_class(
    caplog, emby_image_url
):
    internal = AsyncMock()
    internal.get = AsyncMock(return_value=_FakeResponse(200, content=b"\x89PNG"))
    external = AsyncMock()
    external.post = AsyncMock(side_effect=TimeoutError("timed out"))

    with patch(
        "services.discord._images.get_internal_client", return_value=internal
    ), patch(
        "services.discord._images.get_external_client", return_value=external
    ):
        with caplog.at_level(
            logging.WARNING, logger="mediakeeper.notifications.discord"
        ):
            url = await _upload_emby_to_imgur(emby_image_url, "emby-key", "client-id")

    assert url == ""
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert "exception" in rendered.lower()
    assert "TimeoutError" in rendered
    assert "no-image embed" in rendered
    assert "client-id" not in rendered  # Authorization header value never leaks


@pytest.mark.asyncio
async def test_imgur_emby_pre_fetch_failure_is_logged(caplog, emby_image_url):
    internal = AsyncMock()
    internal.get = AsyncMock(return_value=_FakeResponse(404))
    external = AsyncMock()  # never reached

    with patch(
        "services.discord._images.get_internal_client", return_value=internal
    ), patch(
        "services.discord._images.get_external_client", return_value=external
    ):
        with caplog.at_level(
            logging.WARNING, logger="mediakeeper.notifications.discord"
        ):
            url = await _upload_emby_to_imgur(emby_image_url, "emby-key", "client-id")

    assert url == ""
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert "Emby image fetch failed" in rendered
    assert "status=404" in rendered
    external.post.assert_not_called()


@pytest.mark.asyncio
async def test_imgur_happy_path_returns_link_no_warning(caplog, emby_image_url):
    internal, external = _build_clients(
        emby_response=_FakeResponse(200, content=b"\x89PNG"),
        imgur_response=AsyncMock(),
    )
    success_response = AsyncMock()
    success_response.status_code = 200
    success_response.json = lambda: {"data": {"link": "https://i.imgur.com/x.png"}}
    external.post = AsyncMock(return_value=success_response)

    with patch(
        "services.discord._images.get_internal_client", return_value=internal
    ), patch(
        "services.discord._images.get_external_client", return_value=external
    ):
        with caplog.at_level(
            logging.WARNING, logger="mediakeeper.notifications.discord"
        ):
            url = await _upload_emby_to_imgur(emby_image_url, "emby-key", "client-id")

    assert url == "https://i.imgur.com/x.png"
    # No warning expected for the happy path.
    assert all("Imgur" not in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_imgur_skipped_when_no_client_id():
    """Without a client id we exit early — no log noise, no HTTP call."""
    url = await _upload_emby_to_imgur(
        "http://emby.lan/Items/x/Images/Primary", "emby-key", ""
    )
    assert url == ""
