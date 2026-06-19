"""Help Center service tests — CRUD, soft-delete, restore, purge."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models.portal.help import HelpArticle
from services.portal import help as help_service


@pytest.mark.asyncio
async def test_create_article_creates_slug_and_fr_translation(db_session):
    article = await help_service.create_article(
        db_session,
        category="general",
        title="Comment faire une demande ?",
        body_html="<p>Hello</p>",
        is_draft=False,
    )
    await db_session.commit()
    await db_session.refresh(article)

    assert article.id is not None
    assert article.slug == "comment-faire-une-demande"
    assert article.is_draft is False
    assert len(article.translations) == 1
    assert article.translations[0].lang == "fr"
    assert "<p>Hello</p>" in article.translations[0].body_html


@pytest.mark.asyncio
async def test_create_article_invalid_category_raises(db_session):
    with pytest.raises(ValueError):
        await help_service.create_article(
            db_session, category="bogus",
            title="x", body_html="",
        )


@pytest.mark.asyncio
async def test_upsert_translation_replaces_existing_lang(db_session):
    article = await help_service.create_article(
        db_session, category="general", title="Bonjour", body_html="<p>v1</p>",
    )
    await help_service.upsert_translation(
        db_session, article, lang="fr", title="Bonjour", body_html="<p>v2</p>",
    )
    await db_session.commit()
    await db_session.refresh(article)

    fr = next(t for t in article.translations if t.lang == "fr")
    assert "<p>v2</p>" in fr.body_html


@pytest.mark.asyncio
async def test_upsert_fr_title_realigns_slug(db_session):
    article = await help_service.create_article(
        db_session, category="general", title="Ancien titre", body_html="",
    )
    await help_service.upsert_translation(
        db_session, article, lang="fr",
        title="Nouveau titre clair", body_html="",
    )
    assert article.slug == "nouveau-titre-clair"


@pytest.mark.asyncio
async def test_soft_delete_then_restore(db_session):
    article = await help_service.create_article(
        db_session, category="general", title="A", body_html="",
        is_draft=False,
    )
    await help_service.soft_delete(db_session, article)
    assert article.deleted_at is not None

    # list_published filters deleted articles out.
    visible = await help_service.list_published(db_session)
    assert all(a["id"] != article.id for a in visible)

    await help_service.restore(db_session, article)
    assert article.deleted_at is None


@pytest.mark.asyncio
async def test_purge_expired_only_drops_old_deletes(db_session):
    fresh = await help_service.create_article(
        db_session, category="general", title="Fresh", body_html="",
    )
    stale = await help_service.create_article(
        db_session, category="general", title="Stale", body_html="",
    )
    fresh.deleted_at = datetime.now(timezone.utc) - timedelta(days=5)
    stale.deleted_at = datetime.now(timezone.utc) - timedelta(days=45)
    await db_session.flush()

    purged = await help_service.purge_expired(db_session, threshold_days=30)
    assert purged == 1

    rows = (await db_session.execute(select(HelpArticle.id))).scalars().all()
    assert fresh.id in rows
    assert stale.id not in rows


@pytest.mark.asyncio
async def test_serialize_falls_back_to_default_lang(db_session):
    article = await help_service.create_article(
        db_session, category="general",
        title="Bonjour", body_html="<p>FR only</p>",
    )
    await db_session.commit()
    payload = help_service.serialize(article, lang="en")
    # FR is the only translation present, so it must surface even when
    # the requester asks for English.
    assert payload["title"] == "Bonjour"
    assert payload["lang"] == "fr"
    assert payload["available_langs"] == ["fr"]


# ---------------------------------------------------------------------------
# Admin payload bounds (#412) — body_html is capped to keep a Text column
# and the response payload from growing without limit.
# ---------------------------------------------------------------------------


def test_article_create_payload_caps_body_html():
    from pydantic import ValidationError
    from api.portal.help import ArticleCreatePayload

    ArticleCreatePayload(category="general", title="t", body_html="x" * 100_000)
    with pytest.raises(ValidationError):
        ArticleCreatePayload(category="general", title="t", body_html="x" * 100_001)


def test_translation_payload_caps_body_html():
    from pydantic import ValidationError
    from api.portal.help import TranslationPayload

    TranslationPayload(title="t", body_html="x" * 100_000)
    with pytest.raises(ValidationError):
        TranslationPayload(title="t", body_html="x" * 100_001)
