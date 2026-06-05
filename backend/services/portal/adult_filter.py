"""Adult-content filtering for TMDB-sourced portal catalog responses.

The viewer's ``UserProfile.hide_adult`` preference must drop TMDB items
flagged ``adult`` across every catalog surface (search, recommendations,
person filmography, collection). TMDB's ``adult`` boolean reliably catches
live-action porn but rarely flags animated adult content (hentai) — those
slip through and are tracked separately. Emby-sourced rows (recently added,
Top 20) carry no adult metadata and are filtered elsewhere.
"""


# TMDB keyword IDs for unambiguous pornographic content. Fed to the
# /discover `without_keywords` filter and the request guard. Borderline-but-
# legit markers are deliberately EXCLUDED to avoid hiding mainstream titles:
# erotic (256466 — erotic thrillers), ecchi (195669 — fan-service anime),
# adult animation (161919 — South Park/Rick & Morty), adult humor, sex, nudity.
ADULT_KEYWORD_IDS = (
    198385,   # hentai
    155477,   # softcore
    325693,   # erotica
    445,      # pornography
    5593,     # pornographic video
    272027,   # pornographic animation
    356759,   # porn
    284535,   # adult video
)
ADULT_KEYWORDS_CSV = ",".join(str(k) for k in ADULT_KEYWORD_IDS)
_ADULT_KEYWORD_SET = frozenset(ADULT_KEYWORD_IDS)


def has_adult_keyword(keyword_ids) -> bool:
    """True if any of the item's TMDB keyword IDs marks pornographic content."""
    return bool(_ADULT_KEYWORD_SET.intersection(keyword_ids or ()))


def drop_adult(items: list[dict] | None, hide_adult: bool) -> list[dict]:
    """Remove items flagged ``adult`` when the viewer hides adult content."""
    if not items:
        return items or []
    if not hide_adult:
        return items
    return [it for it in items if not it.get("adult")]
