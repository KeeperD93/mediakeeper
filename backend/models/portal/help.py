"""Portal Help Center — premium articles with multilingual translations.

Two-table design so the catalogue can grow to N languages without future
migrations: ``help_articles`` holds the language-agnostic metadata
(category, slug, icon, ordering, draft/deleted flags) and
``help_article_translations`` carries one row per (article, language) with
the rendered HTML body produced by the WYSIWYG editor.

Soft-delete via ``deleted_at``: the user-facing API filters it out, but
admin can restore within 30 days. A cron sweeps anything older.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from models.base import Base


class HelpArticle(Base):
    __tablename__ = "help_articles"

    id          = Column(Integer, primary_key=True, index=True)
    slug        = Column(String(160), nullable=False, unique=True, index=True)
    category    = Column(String(40), nullable=False, index=True)
    icon        = Column(String(60), nullable=True)
    sort_order  = Column(Integer, nullable=False, server_default="0", index=True)
    is_draft    = Column(Boolean, nullable=False, server_default="false")
    deleted_at  = Column(DateTime(timezone=True), nullable=True, index=True)

    created_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    translations = relationship(
        "HelpArticleTranslation",
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class HelpArticleTranslation(Base):
    __tablename__ = "help_article_translations"
    __table_args__ = (
        UniqueConstraint("article_id", "lang", name="uq_help_article_lang"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    article_id  = Column(
        Integer,
        ForeignKey("help_articles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lang        = Column(String(8), nullable=False, index=True)
    title       = Column(String(300), nullable=False)
    body_html   = Column(Text, nullable=False, server_default="")

    updated_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    article = relationship("HelpArticle", back_populates="translations")
