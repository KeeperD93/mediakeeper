import pytest
from pydantic import ValidationError

from api.portal.news import CreateNews, UpdateNews


def test_news_image_url_accepts_http_urls():
    payload = CreateNews(title="News", content="Content", image_url=" https://example.test/news.png ")

    assert payload.image_url == "https://example.test/news.png"


def test_news_image_url_rejects_non_http_urls():
    with pytest.raises(ValidationError):
        CreateNews(title="News", content="Content", image_url="javascript:alert(1)")

    with pytest.raises(ValidationError):
        UpdateNews(image_url="/api/emby/image/1")
