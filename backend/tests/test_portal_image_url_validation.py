"""Image-URL scheme validation on featured + request payloads.

Both payloads re-serve poster/backdrop URLs into background-image / <img
src> sinks, so a non-http(s) scheme is normalised away at the schema edge.
"""
from urllib.parse import quote

from api.portal.featured import AddFeatured
from api.portal.requests import CreateRequest
from constants.portal_paths import IMAGE_PROXY_PATH
from services.portal.image_cache import proxied_url


def test_featured_drops_unsafe_image_urls():
    f = AddFeatured(
        tmdb_id=1, media_type="movie", title="X",
        poster_url="javascript:alert(1)",
        backdrop="https://image.tmdb.org/t/p/original/x.jpg",
    )
    assert f.poster_url is None
    assert f.backdrop == "https://image.tmdb.org/t/p/original/x.jpg"


def test_request_drops_unsafe_image_urls():
    r = CreateRequest(
        tmdb_id=1, media_type="movie", title="X",
        poster_url="javascript:alert(1)",
        backdrop_url="data:text/html,<script>1</script>",
    )
    assert r.poster_url is None
    assert r.backdrop_url is None


def test_request_keeps_valid_https_image_url():
    r = CreateRequest(
        tmdb_id=1, media_type="movie", title="X",
        poster_url="https://image.tmdb.org/t/p/w500/p.jpg",
    )
    assert r.poster_url == "https://image.tmdb.org/t/p/w500/p.jpg"


def test_request_keeps_tmdb_url_behind_image_cache_url():
    """With the image cache on, cards hand over the local proxy URL."""
    poster = "https://image.tmdb.org/t/p/w300/p.jpg"
    backdrop = "https://image.tmdb.org/t/p/w1280/b.jpg"
    assert proxied_url(poster).startswith(IMAGE_PROXY_PATH)

    r = CreateRequest(
        tmdb_id=1, media_type="movie", title="X",
        poster_url=proxied_url(poster), backdrop_url=proxied_url(backdrop),
    )
    assert r.poster_url == poster
    assert r.backdrop_url == backdrop


def test_request_drops_unsafe_url_behind_image_cache_url():
    r = CreateRequest(
        tmdb_id=1, media_type="movie", title="X",
        poster_url=f"{IMAGE_PROXY_PATH}?u={quote('javascript:alert(1)', safe='')}",
    )
    assert r.poster_url is None
