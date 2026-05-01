"""Help Center service — CRUD, soft-delete, restore, purge, seed.

The user-facing API is read-only and shows only published, non-deleted
articles. The admin API can create / edit / delete / restore. Soft-deleted
articles are kept for 30 days then purged by ``purge_expired``.

HTML sanitization + slug helpers live in ``help_sanitize`` (project
file-size convention: keep individual modules under 300 lines).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.help import HelpArticle, HelpArticleTranslation
from services.portal.help_content import HELP_SEED
from services.portal.help_sanitize import resolve_unique_slug, sanitize_html


VALID_CATEGORIES = (
    "general", "requests", "profile", "lists", "issues", "misc",
)

SUPPORTED_LANGS = ("fr", "en")
DEFAULT_LANG = "fr"

PURGE_AFTER_DAYS = 30


# ─────────────────────────── Read paths ───────────────────────────


async def list_published(db: AsyncSession,
                         lang: str = DEFAULT_LANG) -> list[dict]:
    """Articles for end-users: not deleted, not draft, with the requested
    translation (falls back to ``DEFAULT_LANG`` when missing)."""
    stmt = (
        select(HelpArticle)
        .where(HelpArticle.deleted_at.is_(None))
        .where(HelpArticle.is_draft.is_(False))
        .order_by(HelpArticle.category, HelpArticle.sort_order, HelpArticle.id)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [serialize(article, lang=lang) for article in rows]


async def list_admin(db: AsyncSession, include_deleted: bool = False,
                     lang: str = DEFAULT_LANG) -> list[dict]:
    """Full catalogue for the admin tooling."""
    stmt = select(HelpArticle).order_by(
        HelpArticle.category, HelpArticle.sort_order, HelpArticle.id,
    )
    if not include_deleted:
        stmt = stmt.where(HelpArticle.deleted_at.is_(None))
    rows = (await db.execute(stmt)).scalars().all()
    return [serialize(article, lang=lang, with_admin_meta=True)
            for article in rows]


async def list_trash(db: AsyncSession,
                     lang: str = DEFAULT_LANG) -> list[dict]:
    stmt = (
        select(HelpArticle)
        .where(HelpArticle.deleted_at.is_not(None))
        .order_by(HelpArticle.deleted_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [serialize(article, lang=lang, with_admin_meta=True)
            for article in rows]


async def get_by_slug(db: AsyncSession, slug: str,
                      lang: str = DEFAULT_LANG) -> Optional[dict]:
    stmt = (
        select(HelpArticle)
        .where(HelpArticle.slug == slug)
        .where(HelpArticle.deleted_at.is_(None))
    )
    article = (await db.execute(stmt)).scalar_one_or_none()
    return serialize(article, lang=lang) if article else None


async def get_by_id(db: AsyncSession, article_id: int) -> Optional[HelpArticle]:
    return await db.get(HelpArticle, article_id)


def serialize(article: HelpArticle, *, lang: str = DEFAULT_LANG,
              with_admin_meta: bool = False) -> dict:
    by_lang = {t.lang: t for t in (article.translations or [])}
    primary = by_lang.get(lang) or by_lang.get(DEFAULT_LANG) or next(
        iter(by_lang.values()), None,
    )
    payload: dict = {
        "id": article.id,
        "slug": article.slug,
        "category": article.category,
        "icon": article.icon,
        "sort_order": article.sort_order,
        "title": (primary.title if primary else ""),
        "body_html": (primary.body_html if primary else ""),
        "lang": (primary.lang if primary else lang),
        "available_langs": sorted(by_lang.keys()),
    }
    if with_admin_meta:
        payload.update({
            "is_draft": bool(article.is_draft),
            "deleted_at": (
                article.deleted_at.isoformat() if article.deleted_at else None
            ),
            "translations": {
                t.lang: {"title": t.title, "body_html": t.body_html}
                for t in (article.translations or [])
            },
            "created_at": (
                article.created_at.isoformat() if article.created_at else None
            ),
            "updated_at": (
                article.updated_at.isoformat() if article.updated_at else None
            ),
        })
    return payload


# ─────────────────────────── Write paths ───────────────────────────


async def create_article(db: AsyncSession, *, category: str,
                         title: str, body_html: str,
                         lang: str = DEFAULT_LANG, icon: Optional[str] = None,
                         sort_order: int = 0,
                         is_draft: bool = True) -> HelpArticle:
    if category not in VALID_CATEGORIES:
        raise ValueError("invalid_category")
    if lang not in SUPPORTED_LANGS:
        raise ValueError("invalid_lang")
    article = HelpArticle(
        slug=await resolve_unique_slug(db, title or "article"),
        category=category,
        icon=icon,
        sort_order=sort_order,
        is_draft=is_draft,
    )
    article.translations.append(HelpArticleTranslation(
        lang=lang,
        title=(title or "").strip()[:300],
        body_html=sanitize_html(body_html),
    ))
    db.add(article)
    await db.flush()
    return article


async def update_metadata(db: AsyncSession, article: HelpArticle, *,
                          category: Optional[str] = None,
                          icon: Optional[str] = None,
                          sort_order: Optional[int] = None,
                          is_draft: Optional[bool] = None) -> None:
    if category is not None:
        if category not in VALID_CATEGORIES:
            raise ValueError("invalid_category")
        article.category = category
    if icon is not None:
        article.icon = icon[:60] or None
    if sort_order is not None:
        article.sort_order = int(sort_order)
    if is_draft is not None:
        article.is_draft = bool(is_draft)
    await db.flush()


async def upsert_translation(db: AsyncSession, article: HelpArticle, *,
                             lang: str, title: str, body_html: str) -> None:
    if lang not in SUPPORTED_LANGS:
        raise ValueError("invalid_lang")
    cleaned_title = (title or "").strip()[:300]
    cleaned_body = sanitize_html(body_html)
    existing = next((t for t in article.translations if t.lang == lang), None)
    if existing:
        existing.title = cleaned_title
        existing.body_html = cleaned_body
    else:
        article.translations.append(HelpArticleTranslation(
            lang=lang, title=cleaned_title, body_html=cleaned_body,
        ))
    # Keep the slug aligned with the FR title — it drives deep links.
    if lang == DEFAULT_LANG and cleaned_title:
        article.slug = await resolve_unique_slug(
            db, cleaned_title, exclude_id=article.id,
        )
    await db.flush()


async def soft_delete(db: AsyncSession, article: HelpArticle) -> None:
    article.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def restore(db: AsyncSession, article: HelpArticle) -> None:
    article.deleted_at = None
    await db.flush()


async def hard_delete(db: AsyncSession, article: HelpArticle) -> None:
    await db.delete(article)
    await db.flush()


async def purge_expired(db: AsyncSession,
                        threshold_days: int = PURGE_AFTER_DAYS) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
    stmt = (
        select(HelpArticle)
        .where(HelpArticle.deleted_at.is_not(None))
        .where(HelpArticle.deleted_at < cutoff)
    )
    rows: Iterable[HelpArticle] = (await db.execute(stmt)).scalars().all()
    n = 0
    for article in rows:
        await db.delete(article)
        n += 1
    if n:
        await db.flush()
    return n


# ─────────────────────────── Seed (idempotent) ───────────────────────────


async def ensure_seed(db: AsyncSession) -> int:
    """Create the starter articles if their slug is missing. Never updates
    an existing article — admins are free to rewrite anything without the
    seed silently overwriting their changes on the next boot."""
    created = 0
    for entry in HELP_SEED:
        exists = (await db.execute(
            select(HelpArticle.id).where(HelpArticle.slug == entry["slug"])
        )).scalar_one_or_none()
        if exists:
            continue
        article = HelpArticle(
            slug=entry["slug"],
            category=entry["category"],
            icon=entry.get("icon"),
            sort_order=entry.get("sort_order", 0),
            is_draft=False,
        )
        fr = entry.get("fr") or {}
        article.translations.append(HelpArticleTranslation(
            lang="fr",
            title=fr.get("title", "")[:300],
            body_html=sanitize_html(fr.get("body_html", "")),
        ))
        db.add(article)
        created += 1
    if created:
        await db.commit()
    return created
