"""Help Center seed tests — idempotency + admin override safety.

``ensure_seed`` runs at app boot. It must (a) populate a fresh DB with
the 15 starter articles in French and English, (b) be safe to run
repeatedly without creating duplicates, (c) never overwrite an existing
article — admins are free to rewrite any seeded entry without seeing it
reverted on the next reboot — and (d) give an untouched starter article
of an older install the English text it lacks.
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select

from models.portal.help import HelpArticle, HelpArticleTranslation
from services.portal import help as help_service
from services.portal import help_seed
from services.portal.help_content import HELP_SEED
from services.portal.help_content_en import HELP_EN


async def _langs_by_slug(db) -> dict[str, set[str]]:
    rows = (await db.execute(
        select(HelpArticle.slug, HelpArticleTranslation.lang)
        .join(HelpArticleTranslation, HelpArticleTranslation.article_id == HelpArticle.id)
    )).all()
    out: dict[str, set[str]] = {}
    for slug, lang in rows:
        out.setdefault(slug, set()).add(lang)
    return out


async def _older_install(db) -> None:
    """A database seeded before the English texts existed: French only."""
    await help_seed.ensure_seed(db)
    await db.execute(delete(HelpArticleTranslation).where(HelpArticleTranslation.lang == "en"))
    await db.commit()
    db.expire_all()


def test_every_starter_article_has_an_english_text():
    assert set(HELP_EN) == {entry["slug"] for entry in HELP_SEED}
    for entry in HELP_SEED:
        assert entry["en"]["title"] and entry["en"]["body_html"]


@pytest.mark.asyncio
async def test_first_run_creates_french_and_english(db_session):
    await help_seed.ensure_seed(db_session)
    langs = await _langs_by_slug(db_session)
    assert langs == {entry["slug"]: {"fr", "en"} for entry in HELP_SEED}


@pytest.mark.asyncio
async def test_older_install_gets_english_for_untouched_articles_only(db_session):
    await _older_install(db_session)
    edited_slug, trashed_slug = HELP_SEED[0]["slug"], HELP_SEED[1]["slug"]
    articles = {
        a.slug: a for a in (await db_session.execute(select(HelpArticle))).scalars()
    }
    fr = next(t for t in articles[edited_slug].translations if t.lang == "fr")
    fr.body_html = "<p>Our own rules.</p>"
    articles[trashed_slug].deleted_at = datetime(2026, 11, 1, tzinfo=UTC)
    await db_session.commit()

    assert await help_seed.ensure_seed(db_session) == 0

    langs = await _langs_by_slug(db_session)
    assert langs.pop(edited_slug) == {"fr"}
    assert langs.pop(trashed_slug) == {"fr"}
    assert all(found == {"fr", "en"} for found in langs.values())


@pytest.mark.asyncio
async def test_english_is_added_once(db_session):
    await _older_install(db_session)
    await help_seed.ensure_seed(db_session)
    await help_seed.ensure_seed(db_session)
    total = (await db_session.execute(
        select(func.count(HelpArticleTranslation.id))
        .where(HelpArticleTranslation.lang == "en")
    )).scalar_one()
    assert total == len(HELP_SEED)


async def _first_article(db) -> HelpArticle:
    return (await db.execute(
        select(HelpArticle).where(HelpArticle.slug == HELP_SEED[0]["slug"])
    )).scalar_one()


def _french(article: HelpArticle) -> HelpArticleTranslation:
    return next(t for t in article.translations if t.lang == "fr")


async def _langs_of(db, article_id: int) -> set[str]:
    return set((await db.execute(
        select(HelpArticleTranslation.lang).where(HelpArticleTranslation.article_id == article_id)
    )).scalars())


@pytest.mark.asyncio
@pytest.mark.parametrize("edit", ["title", "image"])
async def test_an_article_the_admin_reshaped_gets_no_english(db_session, edit):
    await _older_install(db_session)
    article = await _first_article(db_session)
    french = _french(article)
    if edit == "title":
        french.title += " !"
    else:  # same words, one more picture
        french.body_html += '<p><img src="https://example.com/a.png" alt=""></p>'
    await db_session.commit()

    await help_seed.ensure_seed(db_session)
    assert await _langs_of(db_session, article.id) == {"fr"}


@pytest.mark.asyncio
async def test_a_re_encoded_starter_text_still_counts_as_untouched(db_session):
    await _older_install(db_session)
    article = await _first_article(db_session)
    french = _french(article)
    # Other spacing, an entity for an accented letter: the same text.
    french.body_html = french.body_html.replace("\n", " ").replace(chr(0xE9), "&eacute;")
    await db_session.commit()

    await help_seed.ensure_seed(db_session)
    assert await _langs_of(db_session, article.id) == {"fr", "en"}


@pytest.mark.asyncio
async def test_rewriting_the_french_drops_the_starter_english(db_session):
    await help_seed.ensure_seed(db_session)
    article = await _first_article(db_session)
    seed_fr = HELP_SEED[0]["fr"]

    # The editor's auto-save sends the text back unchanged: nothing moves.
    await help_service.upsert_translation(
        db_session, article, lang="fr", title=seed_fr["title"], body_html=seed_fr["body_html"],
    )
    await db_session.commit()
    assert await _langs_of(db_session, article.id) == {"fr", "en"}

    # The admin rewrites it: an English reader now gets the admin's French.
    await help_service.upsert_translation(
        db_session, article, lang="fr", title=seed_fr["title"], body_html="<p>Nos propres règles.</p>",
    )
    await db_session.commit()
    assert await _langs_of(db_session, article.id) == {"fr"}


@pytest.mark.asyncio
async def test_ensure_seed_creates_all_articles_first_run(db_session):
    created = await help_seed.ensure_seed(db_session)
    assert created == len(HELP_SEED)

    total = (await db_session.execute(
        select(func.count(HelpArticle.id))
    )).scalar_one()
    assert total == len(HELP_SEED)


@pytest.mark.asyncio
async def test_ensure_seed_is_idempotent(db_session):
    first = await help_seed.ensure_seed(db_session)
    second = await help_seed.ensure_seed(db_session)
    third = await help_seed.ensure_seed(db_session)

    assert first == len(HELP_SEED)
    assert second == 0
    assert third == 0

    total = (await db_session.execute(
        select(func.count(HelpArticle.id))
    )).scalar_one()
    assert total == len(HELP_SEED)


@pytest.mark.asyncio
async def test_ensure_seed_does_not_overwrite_admin_edits(db_session):
    await help_seed.ensure_seed(db_session)
    target_slug = HELP_SEED[0]["slug"]

    article = (await db_session.execute(
        select(HelpArticle).where(HelpArticle.slug == target_slug)
    )).scalar_one()
    fr = next(t for t in article.translations if t.lang == "fr")
    fr.title = "ÉDITION ADMIN"
    fr.body_html = "<p>contenu admin</p>"
    await db_session.flush()

    # Re-running the seed must not revert the admin edit.
    await help_seed.ensure_seed(db_session)

    again = (await db_session.execute(
        select(HelpArticleTranslation)
        .where(HelpArticleTranslation.article_id == article.id)
        .where(HelpArticleTranslation.lang == "fr")
    )).scalar_one()
    assert again.title == "ÉDITION ADMIN"
    assert "contenu admin" in again.body_html


@pytest.mark.asyncio
async def test_a_starter_article_whose_slug_moved_gets_english_and_no_copy(db_session):
    await _older_install(db_session)
    article = await _first_article(db_session)
    article.slug = "moved-by-an-old-editor-save"  # untouched otherwise
    await db_session.commit()

    assert await help_seed.ensure_seed(db_session) == 0  # no copy under the starter slug
    assert await _langs_of(db_session, article.id) == {"fr", "en"}


@pytest.mark.asyncio
async def test_rewriting_the_french_keeps_the_english_the_admin_wrote(db_session):
    await help_seed.ensure_seed(db_session)
    article = await _first_article(db_session)
    await help_service.upsert_translation(
        db_session, article, lang="en", title="Our title", body_html="<p>Our own words.</p>",
    )
    await help_service.upsert_translation(
        db_session, article, lang="fr", title=HELP_SEED[0]["fr"]["title"], body_html="<p>Nos règles.</p>",
    )
    await db_session.commit()
    assert await _langs_of(db_session, article.id) == {"fr", "en"}


@pytest.mark.asyncio
async def test_an_article_the_admin_changed_by_one_word_gets_no_english(db_session):
    await _older_install(db_session)
    article = await _first_article(db_session)
    fr = _french(article)
    fr.body_html = fr.body_html.replace("</p>", " vraiment</p>", 1)
    await db_session.commit()

    await help_seed.ensure_seed(db_session)
    assert await _langs_of(db_session, article.id) == {"fr"}
