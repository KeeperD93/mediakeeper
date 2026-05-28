"""Public path prefixes shared by the portal API surface."""
from typing import Final

__all__ = [
    "IMAGE_PROXY_PATH",
]

#: Public proxy endpoint that streams cached TMDB images.
IMAGE_PROXY_PATH: Final[str] = "/api/img"
