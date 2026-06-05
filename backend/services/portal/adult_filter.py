"""Adult-content filtering for TMDB-sourced portal catalog responses (#289).

The viewer's ``UserProfile.hide_adult`` preference must drop TMDB items
flagged ``adult`` across every catalog surface (search, recommendations,
person filmography, collection). TMDB's ``adult`` boolean reliably catches
live-action porn but rarely flags animated adult content (hentai) — those
slip through and are tracked separately. Emby-sourced rows (recently added,
Top 20) carry no adult metadata and are filtered elsewhere.
"""


def drop_adult(items: list[dict] | None, hide_adult: bool) -> list[dict]:
    """Remove items flagged ``adult`` when the viewer hides adult content."""
    if not items:
        return items or []
    if not hide_adult:
        return items
    return [it for it in items if not it.get("adult")]
