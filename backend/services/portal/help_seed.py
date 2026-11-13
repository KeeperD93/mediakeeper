"""Help Center starter articles: created at boot, given the languages they lack
while untouched, and stripped of their starter translations once the admin
rewrites the French text."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants.portal_content import HELP_LANGS, HELP_SOURCE_LANG
from models.portal.help import HelpArticle, HelpArticleTranslation
from services.portal.help_content import HELP_SEED
from services.portal.help_sanitize import sanitize_html, seeded_as_is

_SEED_BY_SLUG = {entry["slug"]: entry for entry in HELP_SEED}


def _is_starter(translation: HelpArticleTranslation, entry: dict) -> bool:
    seed = entry.get(translation.lang)
    return bool(seed) and translation.title == seed["title"] and seeded_as_is(
        translation.body_html, seed["body_html"],
    )


def _french(article: HelpArticle) -> HelpArticleTranslation | None:
    return next((t for t in article.translations if t.lang == HELP_SOURCE_LANG), None)


async def ensure_seed(db: AsyncSession) -> int:
    """Create the starter articles whose slug is missing, and give a starter
    article the languages it lacks while its French text is untouched. Never
    rewrites a translation: an article the admin edited, or put in the trash,
    stays as it is. Returns the number of articles created."""
    created = 0
    changed = False
    for entry in HELP_SEED:
        article = (await db.execute(
            select(HelpArticle).where(HelpArticle.slug == entry["slug"])
        )).scalar_one_or_none()
        if article is None:
            article = HelpArticle(
                slug=entry["slug"],
                category=entry["category"],
                icon=entry.get("icon"),
                sort_order=entry.get("sort_order", 0),
                is_draft=False,
            )
            db.add(article)
            created += 1
        else:
            french = _french(article)
            if article.deleted_at is not None or french is None or not _is_starter(french, entry):
                continue
        present = {t.lang for t in article.translations}
        for lang in HELP_LANGS:
            if lang in present:
                continue
            article.translations.append(HelpArticleTranslation(
                lang=lang,
                title=entry[lang]["title"][:300],
                body_html=sanitize_html(entry[lang]["body_html"]),
            ))
            changed = True
    if changed:
        await db.commit()
    return created


def drop_stale_starter_translations(article: HelpArticle) -> None:
    """The admin changed a starter article's French text: its other languages,
    still on their starter text, no longer say the same. They go, and readers
    fall back to the admin's French. To call before the slug moves."""
    entry = _SEED_BY_SLUG.get(article.slug)
    french = _french(article)
    if not entry or french is None or _is_starter(french, entry):
        return
    for translation in list(article.translations):
        if translation.lang != HELP_SOURCE_LANG and _is_starter(translation, entry):
            article.translations.remove(translation)
