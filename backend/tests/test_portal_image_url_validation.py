"""Image-URL validation on featured, request and list payloads.

They all re-serve poster/backdrop URLs into background-image / <img src>
sinks, so one rule applies at the edge: the image cache's proxy URL is
undone, then only https on the hosts the CSP lets the portal load.
"""
from urllib.parse import quote

import pytest
from pydantic import ValidationError

from api.portal.featured import AddFeatured, UpdateFeatured
from api.portal.requests import CreateRequest
from constants.portal_paths import IMAGE_PROXY_PATH
from core.security_headers import CSP_DIRECTIVES
from services.portal.image_cache import proxied_url
from services.portal.image_urls import STORED_IMAGE_HOSTS, safe_image_url

TMDB = "https://image.tmdb.org/t/p/w500/p.jpg"
FOREIGN = "https://evil.example/pixel.gif"


def test_featured_drops_unsafe_image_urls():
    f = AddFeatured(
        tmdb_id=1, media_type="movie", title="X",
        poster_url="javascript:alert(1)",
        backdrop="https://image.tmdb.org/t/p/original/x.jpg",
    )
    assert f.poster_url is None
    assert f.backdrop == "https://image.tmdb.org/t/p/original/x.jpg"


def test_featured_keeps_tmdb_url_behind_image_cache_url():
    """With the image cache on, search results carry the local proxy URL."""
    poster = "https://image.tmdb.org/t/p/w300/p.jpg"
    backdrop = "https://image.tmdb.org/t/p/w1280/b.jpg"

    f = AddFeatured(
        tmdb_id=1, media_type="movie", title="X",
        poster_url=proxied_url(poster), backdrop=proxied_url(backdrop),
    )
    assert f.poster_url == poster
    assert f.backdrop == backdrop


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


@pytest.mark.parametrize(("raw", "stored"), [
    (TMDB, TMDB),
    (proxied_url(TMDB), TMDB),
    ("https://i.imgur.com/cover.png", "https://i.imgur.com/cover.png"),
    ("http://image.tmdb.org/t/p/w500/p.jpg", None),
    (FOREIGN, None),
    (f"{IMAGE_PROXY_PATH}?u={quote(FOREIGN, safe='')}", None),
    ("javascript:alert(1)", None),
    ("", None),
    (None, None),
])
def test_one_rule_for_every_stored_image(raw, stored):
    assert safe_image_url(raw) == stored


def test_requests_and_featured_titles_refuse_foreign_or_plain_http_images():
    r = CreateRequest(
        tmdb_id=1, media_type="movie", title="X",
        poster_url=FOREIGN, backdrop_url="http://image.tmdb.org/t/p/w780/b.jpg",
    )
    f = AddFeatured(
        tmdb_id=1, media_type="movie", title="X",
        poster_url=FOREIGN, backdrop="http://image.tmdb.org/t/p/w780/b.jpg",
    )

    assert (r.poster_url, r.backdrop_url, f.poster_url, f.backdrop) == (None, None, None, None)


def test_stored_image_hosts_stay_allowed_by_the_csp():
    """A stored poster on a host the CSP blocks would never show."""
    img_src = next(d for d in CSP_DIRECTIVES.split("; ") if d.startswith("img-src "))
    for host in STORED_IMAGE_HOSTS:
        assert f"https://{host}" in img_src.split()


@pytest.mark.parametrize("vote", [float("nan"), float("inf"), -1, 10.5])
def test_featured_vote_stays_a_tmdb_score(vote):
    """A NaN vote would be stored, then break the JSON of the featured lists."""
    with pytest.raises(ValidationError):
        AddFeatured(tmdb_id=1, media_type="movie", title="X", vote=vote)


@pytest.mark.parametrize("schema, payload", [
    (AddFeatured, {"tmdb_id": 1, "media_type": "movie", "title": "X", "added_by": 7}),
    (UpdateFeatured, {"active": True, "tmdb_id": 2}),
])
def test_featured_schemas_refuse_unknown_fields(schema, payload):
    with pytest.raises(ValidationError):
        schema(**payload)
