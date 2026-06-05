"""Custom uploaded avatars must win over the Emby-proxied URL everywhere.

``resolve_avatar_url`` is the single source of truth for that precedence;
every serializer that exposes an avatar routes through it.
"""
from services.portal.avatars import resolve_avatar_url


def test_resolve_avatar_url_custom_path_wins():
    assert (
        resolve_avatar_url("https://emby.example/photo.png", "17_123.png")
        == "/api/portal/avatars/17_123.png"
    )


def test_resolve_avatar_url_falls_back_to_emby_url():
    assert resolve_avatar_url("/api/emby/user-image/X", None) == "/api/emby/user-image/X"


def test_resolve_avatar_url_none_when_empty():
    assert resolve_avatar_url(None, None) is None
