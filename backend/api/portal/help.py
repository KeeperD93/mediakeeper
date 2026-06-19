"""Help Center endpoints — user (read) + admin (full CRUD).

User surface:
- ``GET  /api/portal/help/articles`` returns the published catalogue,
  optionally filtered by ``?lang=fr|en`` (defaults to the user's profile
  language). The frontend groups results by category client-side.
- ``GET  /api/portal/help/articles/{slug}`` for deep-linking a single
  entry.

Admin surface:
- ``GET  /api/portal/admin/help/articles`` lists everything (incl. drafts).
- ``GET  /api/portal/admin/help/trash`` lists soft-deleted articles still
  inside the 30-day restore window.
- ``POST   /api/portal/admin/help/articles``                  create.
- ``PATCH  /api/portal/admin/help/articles/{id}``             metadata.
- ``PUT    /api/portal/admin/help/articles/{id}/translations/{lang}``
  upsert one (lang) translation. Used by the auto-save loop.
- ``DELETE /api/portal/admin/help/articles/{id}``             soft delete.
- ``POST   /api/portal/admin/help/articles/{id}/restore``     un-delete.
- ``DELETE /api/portal/admin/help/articles/{id}/hard``        permanent.
- ``POST   /api/portal/admin/help/purge``                     expire 30 d+.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile, require_admin
from core.database import get_db
from models.portal.profile import UserProfile
from models.user import User
from services.portal import help as help_service


router = APIRouter(prefix="/help", tags=["portal-help"])
admin_router = APIRouter(
    prefix="/admin/help", tags=["portal-help-admin"],
    dependencies=[Depends(require_admin)],
)


def _resolve_lang(requested: Optional[str], profile: UserProfile) -> str:
    if requested in help_service.SUPPORTED_LANGS:
        return requested  # type: ignore[return-value]
    fallback = (profile.language or help_service.DEFAULT_LANG).lower()
    if fallback in help_service.SUPPORTED_LANGS:
        return fallback
    return help_service.DEFAULT_LANG


# ─────────────────────────── User read ───────────────────────────


@router.get("/articles")
async def list_articles_user(
    lang: Optional[str] = Query(None, max_length=8),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    _, profile = up
    resolved = _resolve_lang(lang, profile)
    items = await help_service.list_published(db, lang=resolved)
    return {"lang": resolved, "items": items}


@router.get("/articles/{slug}")
async def get_article_user(
    slug: str,
    lang: Optional[str] = Query(None, max_length=8),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    _, profile = up
    resolved = _resolve_lang(lang, profile)
    article = await help_service.get_by_slug(db, slug, lang=resolved)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="article_not_found")
    return article


# ─────────────────────────── Admin payloads ───────────────────────────


class ArticleCreatePayload(BaseModel):
    category: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=1, max_length=300)
    body_html: str = Field(default="", max_length=100_000)
    lang: str = Field(default=help_service.DEFAULT_LANG, max_length=8)
    icon: Optional[str] = Field(default=None, max_length=60)
    sort_order: int = Field(default=0)
    is_draft: bool = Field(default=True)


class ArticlePatchPayload(BaseModel):
    category: Optional[str] = Field(default=None, max_length=40)
    icon: Optional[str] = Field(default=None, max_length=60)
    sort_order: Optional[int] = None
    is_draft: Optional[bool] = None


class TranslationPayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    body_html: str = Field(default="", max_length=100_000)


# ─────────────────────────── Admin endpoints ───────────────────────────


@admin_router.get("/articles")
async def list_articles_admin(
    include_deleted: bool = Query(False),
    lang: str = Query(help_service.DEFAULT_LANG, max_length=8),
    db: AsyncSession = Depends(get_db),
):
    items = await help_service.list_admin(
        db, include_deleted=include_deleted, lang=lang,
    )
    return {"items": items}


@admin_router.get("/trash")
async def list_trash(
    lang: str = Query(help_service.DEFAULT_LANG, max_length=8),
    db: AsyncSession = Depends(get_db),
):
    items = await help_service.list_trash(db, lang=lang)
    return {"items": items, "retention_days": help_service.PURGE_AFTER_DAYS}


@admin_router.post("/articles", status_code=status.HTTP_201_CREATED)
async def create_article(
    payload: ArticleCreatePayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        article = await help_service.create_article(
            db,
            category=payload.category,
            title=payload.title,
            body_html=payload.body_html,
            lang=payload.lang,
            icon=payload.icon,
            sort_order=payload.sort_order,
            is_draft=payload.is_draft,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    await db.refresh(article)
    return help_service.serialize(article, lang=payload.lang,
                                  with_admin_meta=True)


@admin_router.patch("/articles/{article_id}")
async def patch_article(
    article_id: int,
    payload: ArticlePatchPayload,
    db: AsyncSession = Depends(get_db),
):
    article = await help_service.get_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article_not_found")
    try:
        await help_service.update_metadata(
            db, article,
            category=payload.category,
            icon=payload.icon,
            sort_order=payload.sort_order,
            is_draft=payload.is_draft,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    await db.refresh(article)
    return help_service.serialize(article, with_admin_meta=True)


@admin_router.put("/articles/{article_id}/translations/{lang}")
async def put_translation(
    article_id: int,
    lang: str,
    payload: TranslationPayload = Body(...),
    db: AsyncSession = Depends(get_db),
):
    article = await help_service.get_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article_not_found")
    try:
        await help_service.upsert_translation(
            db, article,
            lang=lang, title=payload.title, body_html=payload.body_html,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    await db.refresh(article)
    return help_service.serialize(article, lang=lang, with_admin_meta=True)


@admin_router.delete("/articles/{article_id}")
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    article = await help_service.get_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article_not_found")
    await help_service.soft_delete(db, article)
    await db.commit()
    return {"ok": True, "deleted_at": article.deleted_at.isoformat()}


@admin_router.post("/articles/{article_id}/restore")
async def restore_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    article = await help_service.get_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article_not_found")
    await help_service.restore(db, article)
    await db.commit()
    await db.refresh(article)
    return help_service.serialize(article, with_admin_meta=True)


@admin_router.delete("/articles/{article_id}/hard")
async def hard_delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    article = await help_service.get_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article_not_found")
    await help_service.hard_delete(db, article)
    await db.commit()
    return {"ok": True}


@admin_router.post("/purge")
async def purge_trash(
    db: AsyncSession = Depends(get_db),
):
    purged = await help_service.purge_expired(db)
    await db.commit()
    return {"purged": purged}
