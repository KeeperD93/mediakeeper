"""Help Center seed tests — idempotency + admin override safety.

``ensure_seed`` runs at app boot. It must (a) populate a fresh DB with
the 15 starter articles, (b) be safe to run repeatedly without creating
duplicates, and (c) never overwrite an existing article — admins are
free to rewrite any seeded entry without seeing it reverted on the
next reboot.
"""
import pytest
from sqlalchemy import func, select

from models.portal.help import HelpArticle, HelpArticleTranslation
from services.portal import help as help_service
from services.portal.help_content import HELP_SEED


@pytest.mark.asyncio
async def test_ensure_seed_creates_all_articles_first_run(db_session):
    created = await help_service.ensure_seed(db_session)
    assert created == len(HELP_SEED)

    total = (await db_session.execute(
        select(func.count(HelpArticle.id))
    )).scalar_one()
    assert total == len(HELP_SEED)


@pytest.mark.asyncio
async def test_ensure_seed_is_idempotent(db_session):
    first = await help_service.ensure_seed(db_session)
    second = await help_service.ensure_seed(db_session)
    third = await help_service.ensure_seed(db_session)

    assert first == len(HELP_SEED)
    assert second == 0
    assert third == 0

    total = (await db_session.execute(
        select(func.count(HelpArticle.id))
    )).scalar_one()
    assert total == len(HELP_SEED)


@pytest.mark.asyncio
async def test_ensure_seed_does_not_overwrite_admin_edits(db_session):
    await help_service.ensure_seed(db_session)
    target_slug = HELP_SEED[0]["slug"]

    article = (await db_session.execute(
        select(HelpArticle).where(HelpArticle.slug == target_slug)
    )).scalar_one()
    fr = next(t for t in article.translations if t.lang == "fr")
    fr.title = "ÉDITION ADMIN"
    fr.body_html = "<p>contenu admin</p>"
    await db_session.flush()

    # Re-running the seed must not revert the admin edit.
    await help_service.ensure_seed(db_session)

    again = (await db_session.execute(
        select(HelpArticleTranslation)
        .where(HelpArticleTranslation.article_id == article.id)
        .where(HelpArticleTranslation.lang == "fr")
    )).scalar_one()
    assert again.title == "ÉDITION ADMIN"
    assert "contenu admin" in again.body_html
