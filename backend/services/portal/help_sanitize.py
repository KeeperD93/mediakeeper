"""Slug helpers for the Help Center.

The HTML sanitiser used to live here too. It moved to
``_html_sanitize.py`` (Batch 11B) so the GDPR opt-in surface can share
the exact same Tiptap → bleach pipeline. ``sanitize_html`` is still
re-exported from this module so older imports keep working.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.help import HelpArticle
from services.portal._html_sanitize import sanitize_html


__all__ = ["sanitize_html", "slugify", "resolve_unique_slug"]


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(title: str, fallback: str = "article") -> str:
    if not title:
        return fallback
    norm = unicodedata.normalize("NFKD", title)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_RE.sub("-", ascii_only).strip("-")
    return slug or fallback


async def _slug_exists(db: AsyncSession, slug: str,
                       exclude_id: Optional[int] = None) -> bool:
    stmt = select(HelpArticle.id).where(HelpArticle.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(HelpArticle.id != exclude_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def resolve_unique_slug(db: AsyncSession, base: str,
                              exclude_id: Optional[int] = None) -> str:
    candidate = slugify(base)
    if not await _slug_exists(db, candidate, exclude_id=exclude_id):
        return candidate
    for n in range(2, 10000):
        suffixed = f"{candidate}-{n}"
        if not await _slug_exists(db, suffixed, exclude_id=exclude_id):
            return suffixed
    raise RuntimeError("could not resolve unique help slug")
